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

**Solution**:
- Create UUID via `object.__new__(UUID)`
- Set `int` attribute directly
- Bypass `__init__` validation

**Result**: Faster UUID creation from hex strings.

### 8. Enum Value Pre-generation

**Problem**: During deserialization, need to find enum member by value. Default iteration is O(n).

**Solution**: At registration, create `{value: member}` dict for each enum.

**Result**: O(1) lookup instead of iteration.

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

**Code pattern** (serialize.rs):
```rust
let mut buf = arrayvec::ArrayString::<32>::new();
write!(buf, "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}",
    dt.get_year(), dt.get_month(), dt.get_day(),
    dt.get_hour(), dt.get_minute(), dt.get_second()).unwrap();
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

## Type System

### Supported Types

| Type | Notes |
|------|-------|
| `str`, `int`, `float`, `bool` | Direct pass-through |
| `Decimal` | Quantize in Rust, rounding modes via Python |
| `UUID` | Optimized creation (bypass `__init__`) |
| `datetime`, `date`, `time` | `fromisoformat()` in Rust, format support |
| `list[T]`, `set[T]`, `frozenset[T]` | Recursive type handling |
| `dict[K, V]` | Key/value type checking |
| `tuple[T, ...]` | **Homogeneous only** |
| `Optional[T]`, `T \| None` | None handling |
| `Union[T1, T2, ...]` | Try each variant |
| `Enum` | str/int based, pre-generated lookup |
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
