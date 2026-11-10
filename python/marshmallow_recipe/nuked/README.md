# nuked - Technical Design Document

## Purpose & Motivation

The `nuked` module provides significantly faster dataclass serialization/deserialization compared to marshmallow.

**Problem**: marshmallow is too slow for high-throughput scenarios (APIs processing thousands of requests/second).

**Solution**: Rust extension via PyO3 that replaces the hot path (field extraction, type conversion, object construction) with compiled native code.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                       Python Layer                           │
│                                                              │
│  _BuildContext ─→ analyzes dataclass fields & type hints     │
│       │                                                      │
│       ├─ builder.str_field("name", ...)    → FieldHandle     │
│       ├─ builder.int_field("age", ...)     → FieldHandle     │
│       ├─ builder.decimal_field("amt", ...) → FieldHandle     │
│       ├─ builder.dataclass(cls, fields)    → DataclassHandle │
│       ├─ builder.type_dataclass(dc)        → TypeHandle      │
│       └─ builder.build(type_handle)        → Container       │
│                                                              │
│  _container_cache: dict[ContainerKey, Container]             │
│       │                                                      │
│  dump(cls, data) ─→ container.dump(data) ─→ dict/list       │
│  load(cls, data) ─→ container.load(data) ─→ dataclass       │
└──────────────────────────────────────────────────────────────┘
                         ↓ FFI
┌──────────────────────────────────────────────────────────────┐
│                       Rust Layer                             │
│                                                              │
│  ContainerBuilder                                            │
│    ├─ fields: Vec<DataclassField>    (field definitions)     │
│    ├─ dataclasses: Vec<DataclassContainer> (class schemas)   │
│    └─ types: Vec<TypeContainer>      (root type wrappers)    │
│                                                              │
│  Container.dump(obj)                                         │
│    ├─ read slots directly (or getattr fallback)              │
│    ├─ convert each field value via fields/*.rs               │
│    └─ write to presized dict                                 │
│                                                              │
│  Container.load(data)                                        │
│    ├─ iterate input dict                                     │
│    ├─ convert values, track seen fields (SmallBitVec)        │
│    └─ construct dataclass via direct slots (or __init__)     │
└──────────────────────────────────────────────────────────────┘
```

**Note**: Everything runs under GIL (no `allow_threads`).

**Why this split**:
- Python excels at type introspection (dataclasses, typing module)
- Rust excels at fast data processing with no interpreter overhead
- Builder pattern avoids serializing schema info across FFI

## Key Design Decisions

### 1. Why Rust (not Cython/C)

- **PyO3 ecosystem maturity**: Well-maintained, good docs, active community
- **Memory safety**: No segfaults from pointer bugs
- **Feature flags**: PyO3's `uuid` and `chrono` features provide native type conversion

### 2. Builder Pattern

**Problem**: Schema must cross the Python→Rust boundary.

**Solution**: Python calls builder methods directly, receiving opaque handles:

```python
builder = nuked.ContainerBuilder(decimal_places=decimal_places)
ctx = _BuildContext(builder, none_value_handling)
type_handle = ctx.build_root_type(cls, naming_case, set())
container = builder.build(type_handle)
```

Handles are `usize` indices into internal `Vec` storage:
- `FieldHandle` → index into `fields: Vec<DataclassField>`
- `DataclassHandle` → index into `dataclasses: Vec<DataclassContainer>`
- `TypeHandle` → index into `types: Vec<TypeContainer>`

**Result**: No intermediate dict/JSON serialization of schema information.

### 3. Direct Slots Access

**Problem**: `getattr()` for each field adds overhead during serialization.

**Solution**: At build time, Python computes slot offsets via ctypes `_PyMemberDescrObject`. Rust reads/writes slot values directly via pointer arithmetic:

```rust
pub unsafe fn get_slot_value_direct<'py>(
    py: Python<'py>, obj: &Bound<'_, PyAny>, offset: isize,
) -> Option<Bound<'py, PyAny>> {
    let slot_ptr = (obj.as_ptr() as *const u8)
        .offset(offset)
        .cast::<*mut ffi::PyObject>();
    Bound::from_borrowed_ptr_or_opt(py, *slot_ptr)
}

pub unsafe fn set_slot_value_direct(
    obj: &Bound<'_, PyAny>, offset: isize, value: Py<PyAny>,
) -> bool {
    let slot_ptr = obj.as_ptr().cast::<u8>().offset(offset).cast::<*mut ffi::PyObject>();
    let old_ptr = *slot_ptr;
    *slot_ptr = value.into_ptr();
    if !old_ptr.is_null() { ffi::Py_DECREF(old_ptr); }
    true
}
```

**Guard**: Only pointer-aligned offsets are accepted (`offset.cast_unsigned().is_multiple_of(align_of::<*mut PyObject>())`).

**Fallback**: Classes without `__slots__`, or with `__post_init__`, or with `init=False` fields use `getattr`/`__init__`.

### 4. Validators as Python Callables

**Problem**: Reimplementing all Python validation logic in Rust is impractical.

**Solution**: Validators remain Python callables, combined at build time:

```python
def build_combined_validator(validators):
    def combined(value):
        errors = None
        for validator in validators:
            try:
                result = validator(value)
                if result is False:
                    errors = (errors or []) + ["Invalid value."]
            except marshmallow.ValidationError as e:
                errors = (errors or []) + (e.messages if isinstance(e.messages, list) else [e.messages])
            except Exception:
                errors = (errors or []) + ["Invalid value."]
        return errors
    return combined
```

Rust calls the combined validator once per field via FFI. Returned errors are merged into the field's error list.

### 5. Enum Pre-generated Lookup

**Problem**: Finding an enum member by value during deserialization.

**Solution**: At build time, Python passes `[(value, member), ...]` pairs. Rust stores these in type-specific loader data and does linear scan during load:

```rust
// StrEnumLoaderData: values are Rust Strings — fast comparison without Python overhead
for (k, member) in &data.values {
    if k == s {  // Rust string comparison
        return Ok(member.clone_ref(py));
    }
}

// IntEnumLoaderData: values are PyAny — comparison via Python eq
for (k, member) in &data.values {
    if value.eq(k.bind(py)).unwrap_or(false) {
        return Ok(member.clone_ref(py));
    }
}
```

**Default error**: Python generates a descriptive error message at build time: `f"Not a valid enum. Allowed values: {[e.value for e in field_type]}"`.

**Serialization**: Uses `.getattr("value")` to extract the enum member's underlying value, after verifying the value is an instance of the enum class.

### 6. Datetime via chrono

**Problem**: Parsing and formatting datetime strings efficiently.

**Solution**: PyO3's `chrono` feature provides native `DateTime<FixedOffset>` extraction. For formatting, `display_to_py` writes to a stack-allocated `ArrayString` buffer:

```rust
pub fn display_to_py<const N: usize, T: Display>(py: Python<'_>, value: &T) -> Py<PyAny> {
    let mut buf = ArrayString::<N>::new();
    write!(&mut buf, "{value}").expect("buffer overflow");
    PyString::new(py, &buf).into_any().unbind()
}
```

Three datetime formats are supported:
- `Iso` — `DateTime::parse_from_rfc3339()` / `dt.format("%+")`
- `Timestamp` — Unix timestamp as float (microseconds precision)
- `Strftime(String)` — Custom format string via chrono

### 7. UUID via PyO3 uuid Feature

**Problem**: Creating UUID objects efficiently.

**Solution**: PyO3's `uuid` feature enables direct `extract::<::uuid::Uuid>()` and `into_pyobject()` conversion:

```rust
// Load: string → Python UUID
let uuid = ::uuid::Uuid::parse_str(s)
    .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
uuid.into_pyobject(py)

// Dump: Python UUID → string
let uuid: ::uuid::Uuid = value.extract()?;
display_to_py::<36, _>(py, &uuid)  // stack buffer, no heap allocation
```

### 8. Decimal Quantize Caching

**Problem**: `Decimal("0.01")` quantizer recreated on each `quantize()` call.

**Solution**: Static array of `PyOnceLock` caches quantize exponents for decimal places 0–15:

```rust
const MAX_CACHED_PLACES: usize = 16;

static QUANTIZE_EXP_CACHE: [PyOnceLock<Py<PyAny>>; MAX_CACHED_PLACES] =
    [const { PyOnceLock::new() }; MAX_CACHED_PLACES];

fn get_quantize_exp(py: Python<'_>, places: u32) -> PyResult<Bound<'_, PyAny>> {
    let idx = places as usize;
    if idx < MAX_CACHED_PLACES {
        QUANTIZE_EXP_CACHE[idx].get_or_try_init(py, || {
            let exp_str = format!("0.{}", "0".repeat(places as usize));
            get_decimal_cls(py)?.call1((&exp_str,)).map(Bound::unbind)
        }).map(|v| v.bind(py).clone())
    } else {
        // fallback: create without caching
    }
}
```

Quantization is done in Python (`Decimal.quantize()`) — Rust handles the caching of the exponent argument. During dump, when no `rounding` mode is specified, Rust validates the precision instead of quantizing: values with more decimal places than allowed are rejected.

### 9. Presized Lists

**Problem**: Lists reallocate on append.

**Solution**: Pre-allocate exact capacity before populating:

```rust
pub fn new_presized_list(py: Python<'_>, size: usize) -> Bound<'_, PyList> {
    unsafe {
        Bound::from_owned_ptr(py, ffi::PyList_New(size.cast_signed()))
            .cast_into_unchecked()
    }
}
```

### 10. Direct PyList_SET_ITEM

**Problem**: Building a Python list from Rust typically collects into a `Vec<Py<PyAny>>` first, then constructs the list — doubling memory and iteration.

**Solution**: Pre-allocate the list with `PyList_New(size)`, then write items directly:

```rust
let result = new_presized_list(py, items.len());
for (idx, item) in items.iter().enumerate() {
    let dumped = dump_field(item)?;
    unsafe { ffi::PyList_SET_ITEM(result.as_ptr(), idx as isize, dumped.into_ptr()); }
}
```

`PyList_SET_ITEM` steals the reference (`into_ptr()` transfers ownership without INCREF), skips bounds checking, and writes directly to the list's internal array.

### 11. Bitmap for Seen Fields

**Problem**: Tracking which fields were present in the input dict during load.

**Solution**: `SmallBitVec` uses 1 bit per field instead of 1 byte (`Vec<bool>`):

```rust
let mut seen = SmallBitVec::from_elem(self.fields.len(), false);
// ... during iteration:
seen.set(idx, true);
// ... after iteration, check for missing required fields:
if !seen[idx] && !field.optional { /* error */ }
```

For small field counts, storage is inline (no heap allocation). 64-field dataclass: 64 bytes → 8 bytes.

### 12. Interned Strings

**Problem**: Field name comparisons during dict lookup are string comparisons.

**Solution**: All field names and data keys are interned at build time:

```rust
let name_interned = PyString::intern(py, name).unbind();
let data_key_interned = data_key.as_ref().map(|k| PyString::intern(py, k).unbind());
```

Python's string interning guarantees pointer equality for identical strings, making dict key lookups faster.

## Type System

### Supported Types

| Type | Load | Dump |
|------|------|------|
| `str` | pass-through (optional whitespace strip) | pass-through |
| `int` | pass-through (rejects bool) | pass-through |
| `float` | pass-through | pass-through |
| `bool` | pass-through | pass-through |
| `Decimal` | from string/number, optional quantize | validate precision (or quantize with rounding) + format |
| `UUID` | from Python UUID or string (via `uuid` crate) | to hyphenated string |
| `datetime` | ISO/timestamp/strftime (via `chrono`) | ISO/timestamp/strftime |
| `date` | ISO string (via `chrono::NaiveDate`) | ISO string |
| `time` | ISO string (via `chrono::NaiveTime`) | ISO string |
| `list[T]`, `set[T]`, `frozenset[T]` | recursive element conversion | recursive element conversion |
| `dict[K, V]` | recursive value conversion | recursive value conversion |
| `tuple[T, ...]` | **homogeneous only** | homogeneous only |
| `Optional[T]`, `T \| None` | None handling | None handling |
| `Union[T1, T2, ...]` | try each variant | try each variant |
| `StrEnum`, `IntEnum` | lookup by value | `.getattr("value")` |
| Nested dataclass | recursive schema | recursive schema |
| Generic dataclass | TypeVars resolved at build time | TypeVars resolved at build time |
| `Any` | pass-through | pass-through |

## Error Handling

Rust uses a `SerializationError` enum that wraps Python objects directly:

```rust
pub enum SerializationError {
    Single(Py<PyString>),  // single error message
    List(Py<PyList>),      // multiple messages (e.g. ["error1", "error2"])
    Dict(Py<PyDict>),      // nested field errors (e.g. {"field": ["error"]})
}
```

Errors are accumulated during processing into `Option<Bound<'_, PyDict>>` using `accumulate_error`, then converted at the end. At the boundary (Container's `load`/`dump` methods), errors are raised directly as `marshmallow.ValidationError` — no intermediate `ValueError` or Python-side conversion needed:

```rust
fn load(&self, py: Python<'_>, data: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    self.inner.load_from_py(py, data).map_err(|e| e.to_validation_err(py))
}
```

The `to_validation_err` method caches the `marshmallow.ValidationError` class via `PyOnceLock` and constructs the exception directly in Rust.

## Limitations & Trade-offs

1. **Only homogeneous tuples** — `tuple[int, ...]` works, `tuple[int, str]` doesn't
2. **Heterogeneous unions are slower** — try-catch on each variant until one succeeds
3. **`__post_init__` disables direct slots** — falls back to `__init__`-based construction
4. **`init=False` fields require special handling** — set after object creation
5. **Cyclic dataclass references** — not supported, raises `NotImplementedError`
6. **Validators remain in Python** — FFI overhead per validator call, but keeps validators flexible
