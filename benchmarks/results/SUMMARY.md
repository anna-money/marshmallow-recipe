# Benchmark Summary: dump_to_bytes / load_from_bytes

## Setup
- Model: TransactionData (18 fields, nested objects, UUID, Decimal, datetime, StrEnum)
- Python 3.12, Rust release build with LTO

## Results

### Single Object (TransactionData with nested)

| Operation | Time (us) | vs Baseline | Speedup |
|---|---|---|---|
| nuked.dump | 5.88 | - | - |
| nuked.dump + json.dumps | 10.44 | baseline | 1.0x |
| **dump_to_bytes** | **5.07** | **vs dump+json.dumps** | **2.06x** |
| nuked.load | 8.91 | - | - |
| json.loads + nuked.load | 13.63 | baseline | 1.0x |
| load_from_bytes | 13.60 | vs loads+load | 1.00x |

### Batch (100 items)

| Operation | Time (us) | vs Baseline | Speedup |
|---|---|---|---|
| nuked.dump 100 | 326.68 | - | - |
| nuked.dump + json.dumps 100 | 486.50 | baseline | 1.0x |
| **dump_to_bytes 100** | **220.68** | **vs dump+json.dumps** | **2.20x** |
| nuked.load 100 | 465.50 | - | - |
| json.loads + nuked.load 100 | 632.90 | baseline | 1.0x |
| load_from_bytes 100 | 695.01 | vs loads+load | 0.91x |

### Comparison with marshmallow (single)

| Operation | marshmallow (us) | nuked bytes (us) | Speedup |
|---|---|---|---|
| dump | 136.16 | 5.07 (dump_to_bytes) | **26.9x** |
| load | 84.05 | 13.60 (load_from_bytes) | **6.2x** |

## Key Findings

1. **dump_to_bytes is 2x faster** than dump+json.dumps because it eliminates intermediate Python dict and per-field Python object allocations
2. **load_from_bytes shows no improvement** over json.loads+load because serde_json::Value allocation cost is similar to Python json.loads
3. **dump_to_bytes is 27x faster than marshmallow dump** for the full dump+encode path
4. For maximum performance, use `dump_to_bytes` for serialization and `json.loads + nuked.load` for deserialization
