# nuked - Technical Design Document

## Purpose & Motivation

The `nuked` module provides significantly faster dataclass serialization/deserialization compared to marshmallow.

**Problem**: marshmallow is too slow for high-throughput scenarios (APIs processing thousands of requests/second).

**Solution**: Rust extension via PyO3 that replaces the hot path (JSON parsing, field extraction, object construction) with compiled native code.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ _descriptor  │  │   _schema    │  │   _validator     │  │
│  │ Type analysis│  │ Dict convert │  │ Pre-built tree   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                           ↓                                 │
│                    register(schema_id, dict)                │
└─────────────────────────────────────────────────────────────┘
                            ↓ FFI (single entry point)
┌─────────────────────────────────────────────────────────────┐
│                      Rust Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │    cache     │  │  *_bytes     │  │    serialize     │  │
│  │ Schema store │  │ JSON parse   │  │   deserialize    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Note**: Everything runs under GIL (no `allow_threads`).

**Why this split**:
- Python excels at type introspection (dataclasses, typing module)
- Rust excels at fast data processing (serde_json >> Python json)
- Compiled Rust code has no interpreter overhead
- Single FFI boundary crossing (enter once, do all work in Rust)

## Key Design Decisions

### 1. Why Rust (not Cython/C)

- **PyO3 ecosystem maturity**: Well-maintained, good docs, active community
- **serde_json performance**: Battle-tested, highly optimized JSON parser
- **Memory safety**: No segfaults from pointer bugs

### 2. Schema Caching Strategy

**Problem**: Each dump/load call required building the schema from Python type hints.

**Solution**:
- Python analyzes types once at first use
- Converts to dict and calls `register(schema_id, dict)`
- Rust parses dict into `TypeDescriptor` and caches in `SCHEMA_CACHE`
- Subsequent calls use only the integer schema_id

**Result**: Significantly faster for bulk operations.

### 3. Direct Slots Access

**Problem**: FFI overhead on `getattr()` for each field during serialization.

**Solution**:
- At registration, get slot offset via `PyMemberDescrObject`
- Store offset in `FieldDescriptor`
- During dump, read slot values directly via pointer arithmetic
- Fallback to `getattr` for non-slotted classes

**Result**: +30% faster for slotted dataclasses.

### 4. Validators as Python Callables

**Problem**: Writing validators in pure Rust would require reimplementing all Python validation logic.

**Solution**:
- Validators remain as Python callables
- Combined into single function at registration time (`build_combined_validator`)
- Rust calls these Python functions via FFI during dump/load
- Validation errors collected and converted to `marshmallow.ValidationError`

**Trade-off**: FFI overhead per validator call, but keeps validators flexible and compatible with existing code.

### 5. Two APIs: dump vs dump_to_bytes

**Problem**: Not always need bytes, sometimes need dict for further processing (e.g., adding fields before JSON encoding).

**Solution**: Two APIs:
- `dump(cls, obj)` → Python dict/list
- `dump_to_bytes(cls, obj)` → JSON bytes

See **Performance Characteristics** section for benchmarks.

### 6. Decimal Quantize Caching

**Problem**: `Decimal("0.01")` quantizer created on each `quantize()` call.

**Solution**: Pre-cache quantizers for common decimal places (0-8 and 12).

**Result**: Fewer Python object allocations.

### 7. UUID Optimization

**Problem**: `uuid.UUID(hex=...)` does validation (check length, valid hex chars, etc.).

**Solution**: Use `PyObject_Vectorcall` to call `UUID(None, None, None, None, int_value)` directly via C API.

**Code pattern** (cache.rs):
```rust
pub fn create_uuid_fast(&self, py: Python, uuid_int: u128) -> PyResult<Py<PyAny>> {
    let int_obj = uuid_int.into_pyobject(py)?;
    let none = unsafe { ffi::Py_None() };
    let args: [*mut ffi::PyObject; 5] = [none, none, none, none, int_obj.as_ptr()];
    let result = unsafe {
        ffi::PyObject_Vectorcall(self.uuid_cls.as_ptr(), args.as_ptr(), 5, std::ptr::null_mut())
    };
    // ...
}
```

**Why vectorcall**: This is the official Python C API for fast function calls. It avoids tuple allocation for arguments and uses a flat array instead. Cleaner and more maintainable than bypassing `__init__` with internal attribute manipulation.

**Result**: Faster UUID creation from hex strings without relying on internal implementation details.

### 8. Enum Optimizations

#### 8a. Value Pre-generation (Deserialization)

**Problem**: During deserialization, need to find enum member by value. Default iteration is O(n).

**Solution**: At registration, create `{value: member}` dict for each enum.

**Result**: O(1) lookup instead of iteration.

#### 8b. Direct Type Cast (Serialization)

**Problem**: Accessing `.value` attribute on enum members requires Python attribute lookup.

**Solution**: Since `StrEnum` inherits from `str` and `IntEnum` inherits from `int`, use direct type cast instead.

**Code pattern** (serialize.rs):
```rust
FieldType::StrEnum => {
    if let Some(ref enum_cls) = field.enum_cls {
        if !value.is_instance(enum_cls.bind(ctx.py))? {
            // ... error handling
        }
    }
    Ok(value.cast::<PyString>()?.to_owned().into_any().unbind())
}
FieldType::IntEnum => {
    // ... same validation pattern
    Ok(value.cast::<PyInt>()?.to_owned().into_any().unbind())
}
```

**Why it works**: Python's `StrEnum` and `IntEnum` are subclasses of `str` and `int` respectively. PyO3's `cast::<PyString>()` directly accesses the string value without going through Python's attribute protocol.

**Result**: Faster serialization by avoiding `.value` attribute lookup.

### 9. Zero-Copy String Operations

**Problem**: JSON parsing typically allocates new `String` for each key and value.

**Solution**:
- `next_key::<&str>()` instead of `next_key::<String>()` — borrows directly from serde_json's internal buffer
- `visit_str(&str)` in deserializer — receives borrowed slice, no allocation
- Keys are only copied when creating Python objects

**How it works**: serde_json keeps the entire JSON input in memory. When we request `&str`, we get a pointer into that buffer. Allocation only happens when creating Python strings.

### 10. DateTime/Date/Time Optimizations

**Problem**: Python datetime formatting via `strftime()` is slow and heap-allocates.

**Solution**:
- **Direct field access**: `dt.get_year()` reads from CPython's C struct directly instead of calling Python method `dt.year`
- **Stack buffers**: `ArrayString::<32>` is fixed-size array on stack, no heap allocation
- **Inline formatting**: `write!(buf, "{:04}-{:02}-{:02}T...", year, month, day)` — no intermediate strings
- **Timezone handling**: `PyDeltaAccess` extracts offset components directly (`get_days()`, `get_seconds()`)
- **UTC fast-path**: Direct pointer comparison with cached `datetime.UTC` to skip `utcoffset()` call
- **jiff library**: Uses `jiff` crate for datetime parsing (replaced `chrono`) — modern, well-maintained

**Code pattern** (serialize.rs):
```rust
let mut buf = arrayvec::ArrayString::<32>::new();
write!(buf, "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}",
    dt.get_year(), dt.get_month(), dt.get_day(),
    dt.get_hour(), dt.get_minute(), dt.get_second()).unwrap();
```

**UTC fast-path code** (serialize.rs):
```rust
fn get_tz_offset_seconds(py: Python, tz: &Bound<'_, PyTzInfo>, reference: &Bound<'_, PyAny>) -> PyResult<i32> {
    let cached = get_cached_types(py)?;
    if tz.is(cached.utc_tz.bind(py)) {
        return Ok(0);  // Skip utcoffset() call for UTC
    }
    let offset = tz.call_method1(cached.str_utcoffset.bind(py), (reference,))?;
    // ...
}
```

### 11. Collection Type Handling

**Problem**: Generic `PyAny` iteration requires type checks on each element.

**Solution**:
- Downcast once to specific type: `value.cast::<PySet>()?`
- Use type-specific iterators: `set.iter()` knows element type
- `is_instance_of::<PySet>()` — single type check vs multiple isinstance calls

**Why it's faster**: PyO3's native type iterators skip Python's generic iteration protocol.

### 12. Bitmap for Seen Fields

**Problem**: Tracking seen fields with `Vec<bool>` uses 1 byte per field.

**Solution** (only in `deserialize_bytes.rs`):
- `SmallBitVec::from_elem(fields.len(), false)` — 1 bit per field
- `seen_fields.set(idx, true)` / `seen_fields[idx]` — bit operations

**Note**: `deserialize.rs` (dict → dataclass) still uses `Vec<bool>` because the overhead is negligible for dict iteration.

**Memory**: 64-field dataclass: 64 bytes → 8 bytes.

### 13. Decimal Rust-Side Rounding

**Problem**: Traditional approach creates intermediate Python `Decimal` object just to quantize it.

**Solution**: Parse string with `rust_decimal` crate, round in Rust, pass pre-formatted string to Python `Decimal()`.

**Code pattern** (deserialize_bytes.rs):
```rust
fn create_decimal_from_str<E: de::Error>(&self, s: &str) -> Result<Py<PyAny>, E> {
    let py = self.ctx.py;
    let cached = get_cached_types(py).map_err(E::custom)?;

    // Determine decimal places from field or global settings
    let places = match self.field.decimal_places {
        DecimalPlaces::NoRounding => None,
        DecimalPlaces::Places(n) => Some(n),
        DecimalPlaces::NotSpecified => self.ctx.decimal_places.or(Some(2)),
    };

    if let Some(places) = places.filter(|&p| p >= 0) {
        // Parse and round in Rust — much faster than Python
        if let Ok(mut rust_decimal) = Decimal::from_str(s) {
            let strategy = python_rounding_to_rust(self.field.decimal_rounding.as_ref(), py);
            rust_decimal = rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy);
            // Create Python Decimal with pre-formatted string
            let formatted = format!("{:.prec$}", rust_decimal, prec = places.cast_unsigned() as usize);
            return cached.decimal_cls.bind(py).call1((&formatted,))
                .map(pyo3::Bound::unbind)
                .map_err(E::custom);
        }
    }

    // Fallback: create Python Decimal directly from input string
    cached.decimal_cls.bind(py).call1((s,))
        .map(pyo3::Bound::unbind)
        .map_err(E::custom)
}
```

**Why it's faster**:
- `rust_decimal` crate is a native Rust library (not Python)
- Rounding happens entirely in compiled code
- Only one Python object created (final result), not intermediate
- Avoids calling Python's `Decimal.quantize()` method

**Result**: Faster decimal deserialization with built-in rounding support.

## Type System

### Supported Types

| Type | Notes |
|------|-------|
| `str`, `int`, `float`, `bool` | Direct pass-through |
| `Decimal` | Rust-side rounding with `rust_decimal` crate |
| `UUID` | Optimized creation via vectorcall |
| `datetime`, `date`, `time` | `fromisoformat()` in Rust, format support |
| `list[T]`, `set[T]`, `frozenset[T]` | Recursive type handling |
| `dict[K, V]` | Key/value type checking |
| `tuple[T, ...]` | **Homogeneous only** |
| `Optional[T]`, `T \| None` | None handling |
| `Union[T1, T2, ...]` | Try each variant |
| `Enum` | str/int based, pre-generated lookup, direct type cast |
| Nested dataclass | Recursive schema |
| Generic dataclass | TypeVars resolved at registration |
| `Any` | Pass-through without transformation |

## Error Handling

### Validation Errors

- Rust returns `ValueError` with JSON dict
- Python converts to `marshmallow.ValidationError`
- Format: `{"field": ["message"]}`

### Custom Error Messages

Supported via field metadata:
- `required_error` - when required field is missing
- `none_error` - when field is None but shouldn't be
- `invalid_error` - for type validation errors

### Serde Location Cleanup

serde appends ` at line X column Y` to nested errors:
```
{"list": {"0": {"item": ["error"]} at line 1 column 30}} at line 1 column 50
```

Python regex cleans this before parsing.

## Performance Characteristics

Run benchmarks to measure performance on your hardware:

```bash
uv run python benchmarks/bench_serialization.py
```

Benchmarks use TransactionData model (nested dataclass with 15+ fields).

### Remaining Bottlenecks (all under GIL)

1. **Python↔Rust FFI boundary** - minimized to single entry/exit
2. **Python object creation in Rust** - PyDict, PyList, dataclass instances
3. **Validator callbacks** - moved to Python layer, executed in batch

### Optimizations Applied

- **Zero-copy strings** - no intermediate String allocations
- **Stack buffers** - ArrayString for datetime formatting (no heap)
- **Direct field access** - PyDateAccess/PyTimeAccess instead of method calls
- **Bitmap tracking** - 1 bit per field instead of 1 byte

## Limitations & Trade-offs

1. **Only homogeneous tuples** - `tuple[int, ...]` works, `tuple[int, str]` doesn't
2. **Heterogeneous unions are slower** - try-catch on each variant until one succeeds
3. **`__post_init__` disables direct slots optimization** - falls back to regular instantiation
4. **`init=False` fields require special handling** - need to be set after object creation

## File Structure

```
marshmallow_recipe/nuked/
├── __init__.py      # Public API: dump, dump_to_bytes, load, load_from_bytes
├── _descriptor.py   # TypeDescriptor, FieldDescriptor, SchemaDescriptor
├── _schema.py       # descriptor_to_dict conversion for Rust
├── _validator.py    # Pre-built validation tree
└── README.md        # This file

src/
├── lib.rs               # PyO3 module entry point
├── api.rs               # Python-callable functions
├── cache.rs             # SCHEMA_CACHE, type descriptor building
├── types.rs             # Rust type definitions
├── deserialize.rs       # Dict → dataclass
├── serialize.rs         # Dataclass → dict
├── deserialize_bytes.rs # JSON bytes → dataclass
├── serialize_bytes.rs   # Dataclass → JSON bytes
├── slots.rs             # Direct slot access optimization
├── encoding.rs          # Character encoding conversion
└── utils.rs             # Shared utilities (JSON value conversion)
```
