# Type Handling Reference

Этот документ описывает где найти логику обработки каждого типа.

## Быстрый поиск: "Как сериализуется тип X?"

| Type | Serialize (dict) | Serialize (json) | Deserialize (dict) | Deserialize (json) |
|------|-----------------|------------------|--------------------|--------------------|
| **Str** | serialize.rs:93-106 | serialize_bytes.rs:140-165 | deserialize.rs:115-130 | deserialize_bytes.rs:420-440 |
| **Int** | serialize.rs:107-114 | serialize_bytes.rs:166-180 | deserialize.rs:131-145 | deserialize_bytes.rs:441-465 |
| **Bool** | serialize.rs:116-124 | serialize_bytes.rs:181-195 | deserialize.rs:146-160 | deserialize_bytes.rs:466-480 |
| **Float** | serialize.rs:125-149 | serialize_bytes.rs:196-225 | deserialize.rs:161-180 | deserialize_bytes.rs:481-510 |
| **Decimal** | serialize.rs:150-185 | serialize_bytes.rs:226-280 | deserialize.rs:181-220 | deserialize_bytes.rs:511-560 |
| **Uuid** | serialize.rs:186-199 | serialize_bytes.rs:281-310 | deserialize.rs:221-245 | deserialize_bytes.rs:561-590 |
| **DateTime** | serialize.rs:200-254 | serialize_bytes.rs:311-370 | deserialize.rs:246-295 | deserialize_bytes.rs:591-650 |
| **Date** | serialize.rs:255-266 | serialize_bytes.rs:371-395 | deserialize.rs:296-315 | deserialize_bytes.rs:651-680 |
| **Time** | serialize.rs:267-281 | serialize_bytes.rs:396-425 | deserialize.rs:316-340 | deserialize_bytes.rs:681-715 |
| **List** | serialize.rs:282-312 | serialize_bytes.rs:426-470 | deserialize.rs:341-385 | deserialize_bytes.rs:716-770 |
| **Dict** | serialize.rs:313-344 | serialize_bytes.rs:471-520 | deserialize.rs:386-430 | deserialize_bytes.rs:771-830 |
| **Nested** | serialize.rs:345-357 | serialize_bytes.rs:521-555 | deserialize.rs:431-470 | deserialize_bytes.rs:831-880 |
| **StrEnum** | serialize.rs:358-378 | serialize_bytes.rs:556-585 | deserialize.rs:471-500 | deserialize_bytes.rs:881-920 |
| **IntEnum** | serialize.rs:358-378 | serialize_bytes.rs:556-585 | deserialize.rs:471-500 | deserialize_bytes.rs:881-920 |
| **Set** | serialize.rs:379-422 | serialize_bytes.rs:586-630 | deserialize.rs:501-540 | deserialize_bytes.rs:921-970 |
| **FrozenSet** | serialize.rs:379-422 | serialize_bytes.rs:586-630 | deserialize.rs:541-580 | deserialize_bytes.rs:971-1020 |
| **Tuple** | serialize.rs:379-422 | serialize_bytes.rs:631-675 | deserialize.rs:581-620 | deserialize_bytes.rs:1021-1070 |
| **Union** | serialize.rs:423-450 | serialize_bytes.rs:676-720 | deserialize.rs:621-670 | deserialize_bytes.rs:1071-1130 |
| **Any** | serialize.rs:451-460 | serialize_bytes.rs:721-740 | deserialize.rs:671-690 | deserialize_bytes.rs:1131-1150 |

## Shared Utilities (utils.rs)

### High-level Type Helpers (Single Source of Truth)

| Function/Struct | Purpose | Used by |
|-----------------|---------|---------|
| `DateTimeComponents` | Struct holding all datetime parts | serialize.rs, serialize_bytes.rs |
| `extract_datetime_components()` | Extract components from PyDateTime | serialize.rs, serialize_bytes.rs |
| `serialize_datetime_to_iso()` | Format datetime to ISO string | serialize.rs, serialize_bytes.rs |
| `serialize_datetime_with_format()` | Format datetime with custom strftime | serialize.rs, serialize_bytes.rs |
| `format_uuid_to_buf()` | Format UUID to hyphenated string | serialize.rs, serialize_bytes.rs |
| `DecimalResult` | Enum for decimal processing result | serialize.rs, serialize_bytes.rs |
| `process_decimal_for_serialization()` | Process decimal with places/rounding | serialize.rs, serialize_bytes.rs |

### Low-level Formatting Functions

| Function | Purpose | Used by |
|----------|---------|---------|
| `format_datetime_to_buf()` | Low-level datetime buffer format | DateTime serialize |
| `format_datetime_with_strftime()` | Low-level strftime format | DateTime serialize |
| `format_date_to_buf()` | Format date to ISO string | Date serialize |
| `format_time_to_buf()` | Format time to ISO string | Time serialize |

### Parsing Functions (Deserialize)

| Function | Purpose | Used by |
|----------|---------|---------|
| `parse_rfc3339_datetime()` | Parse ISO datetime | DateTime deserialize |
| `parse_datetime_with_format()` | Parse custom format datetime | DateTime deserialize |
| `parse_iso_date()` | Parse ISO date | Date deserialize |
| `parse_iso_time()` | Parse ISO time | Time deserialize |

### Python Object Creation (Deserialize)

| Function | Purpose | Used by |
|----------|---------|---------|
| `create_pydatetime_from_speedate()` | Create Python datetime | DateTime deserialize |
| `create_pydate_from_speedate()` | Create Python date | Date deserialize |
| `create_pytime_from_speedate()` | Create Python time | Time deserialize |

### Other Utilities

| Function | Purpose | Used by |
|----------|---------|---------|
| `get_tz_offset_seconds()` | Get timezone offset | DateTime/Time serialize |
| `python_rounding_to_rust()` | Convert rounding strategy | Decimal |

## Architecture Notes

### Why 4 files?

Codebase has 4 serialization paths for different use cases:

1. **serialize.rs** - Python object → Python dict (for compatibility)
2. **deserialize.rs** - Python dict → Python object (for compatibility)
3. **serialize_bytes.rs** - Python object → JSON bytes (high performance, uses serde)
4. **deserialize_bytes.rs** - JSON bytes → Python object (high performance, uses serde)

### Why not trait-based handlers?

Trait-based approach was evaluated but rejected because:
1. **Dynamic dispatch overhead** - vtable lookups on hot path
2. **String allocations** - error messages would need owned Strings
3. **No real benefit** - match statements are optimized by LLVM into jump tables

### How to add a new type?

1. Add variant to `FieldType` enum in `types.rs`
2. Add parsing in `FieldType::from_str()` in `types.rs`
3. Add serialize arm in `serialize.rs:serialize_field_value()`
4. Add serialize arm in `serialize_bytes.rs:FieldValueSerializer::serialize()`
5. Add deserialize arm in `deserialize.rs:deserialize_field_value()`
6. Add deserialize arm in `deserialize_bytes.rs:FieldValueVisitor`
7. Add any shared utilities to `utils.rs`
8. Update this document

### Performance considerations

- All type checks use `is_instance_of::<T>()` which is fast
- Buffer-based formatting (ArrayString) avoids heap allocations
- `#[inline]` on hot paths
- `#[cold]` on error paths to hint optimizer
- No trait objects in serialization path
