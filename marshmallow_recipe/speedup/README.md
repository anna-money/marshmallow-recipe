# speedup - Technical Design Document

## Purpose & Motivation

The `speedup` module provides 10-30x faster dataclass serialization/deserialization compared to marshmallow.

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
│  │    cache     │  │  streaming   │  │  serialize_dict  │  │
│  │ Schema store │  │ JSON parse   │  │  deserialize_dict│  │
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

**Commit**: `3da0542`

**Problem**: Each dump/load call required building the schema from Python type hints.

**Solution**:
- Python analyzes types once at first use
- Converts to dict and calls `register(schema_id, dict)`
- Rust parses dict into `TypeDescriptor` and caches in `SCHEMA_CACHE`
- Subsequent calls use only the integer schema_id

**Result**: 12-13x speedup for bulk operations.

### 3. Direct Slots Access

**Commits**: `f7b92dd`, `f16ad95`

**Problem**: FFI overhead on `getattr()` for each field during serialization.

**Solution**:
- At registration, get slot offset via `PyMemberDescrObject`
- Store offset in `FieldDescriptor`
- During dump, read slot values directly via pointer arithmetic
- Fallback to `getattr` for non-slotted classes

**Result**: +30% faster for slotted dataclasses.

### 4. Validators in Python (not Rust)

**Commit**: `38c4fd1`

**Problem**: Calling Python callable from Rust has FFI overhead on each call (PyObject creation, call dispatch). With validators in Rust, each field validation required crossing FFI boundary.

**Solution**:
- Build validation tree once in Python (`Validator` class)
- Execute validation before dump and after load (in Python)
- Rust only does type coercion, not validation

**Result**: 11-22x faster vs v1 (was worse with validators in Rust due to FFI overhead per field).

### 5. Two APIs: dump vs dump_to_bytes

**Commit**: `6ea2571`

**Problem**: Not always need bytes, sometimes need dict for further processing (e.g., adding fields before JSON encoding).

**Solution**: Two APIs:
- `dump(cls, obj)` → Python dict/list
- `dump_to_bytes(cls, obj)` → JSON bytes

**Performance** (vs marshmallow):
- dump: 20-32x faster
- load: 9-14x faster

### 6. Decimal Quantize Caching

**Commit**: `c1cb23b`

**Problem**: `Decimal("0.01")` quantizer created on each `quantize()` call.

**Solution**: Pre-cache quantizers for common decimal places (0-8 and 12).

**Result**: Fewer Python object allocations.

### 7. UUID Optimization

**Commit**: `09dcc57`

**Problem**: `uuid.UUID(hex=...)` does validation (check length, valid hex chars, etc.).

**Solution**:
- Create UUID via `object.__new__(UUID)`
- Set `int` attribute directly
- Bypass `__init__` validation

**Result**: Faster UUID creation from hex strings.

### 8. Enum Value Pre-generation

**Commit**: `c041c66`

**Problem**: During deserialization, need to find enum member by value. Default iteration is O(n).

**Solution**: At registration, create `{value: member}` dict for each enum.

**Result**: O(1) lookup instead of iteration.

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

| Operation | vs marshmallow |
|-----------|----------------|
| dump (dict) | 20-32x |
| dump_to_bytes | 11-22x |
| load (dict) | 9-14x |
| load_from_bytes | 11-22x |

### Bottlenecks (all under GIL)

1. **Python↔Rust FFI boundary** - minimized to single entry/exit
2. **Python object creation in Rust** - PyDict, PyList, dataclass instances
3. **Validator callbacks** - moved to Python layer, executed in batch

## Limitations & Trade-offs

1. **Only homogeneous tuples** - `tuple[int, ...]` works, `tuple[int, str]` doesn't
2. **Heterogeneous unions are slower** - try-catch on each variant until one succeeds
3. **`__post_init__` disables direct slots optimization** - falls back to regular instantiation
4. **`init=False` fields require special handling** - need to be set after object creation

## File Structure

```
marshmallow_recipe/speedup/
├── __init__.py      # Public API: dump, dump_to_bytes, load, load_from_bytes
├── _descriptor.py   # TypeDescriptor, FieldDescriptor, SchemaDescriptor
├── _schema.py       # descriptor_to_dict conversion for Rust
├── _validator.py    # Pre-built validation tree
└── README.md        # This file

packages/marshmallow-recipe-speedup/src/
├── lib.rs              # PyO3 module entry point
├── api.rs              # Python-callable functions
├── cache.rs            # SCHEMA_CACHE, type descriptor building
├── types.rs            # Rust type definitions
├── deserialize_dict.rs # Dict → dataclass
├── serialize_dict.rs   # Dataclass → dict
├── streaming.rs        # JSON bytes → dataclass
├── serialize_streaming.rs # Dataclass → JSON bytes
├── slots.rs            # Direct slot access optimization
└── encoding.rs         # Character encoding conversion
```
