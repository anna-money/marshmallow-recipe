# Alternative Architecture: Module-per-Type (Zero Overhead)

## Problem
Текущая архитектура имеет 4 файла с огромными match statements. Сложно понять как обрабатывается конкретный тип.

## Rejected Solution: Trait-based Handlers
❌ Добавляет overhead:
- Dynamic dispatch (vtable)
- String allocations для error messages
- Box/Py аллокации

## Proposed Solution: Inline Functions + Reference Doc

Вместо изменения архитектуры, создаём **документацию-справочник** и **inline функции** для переиспользования.

### Option 1: Documentation-only (Zero Changes)

Создать `docs/TYPE_REFERENCE.md` с точными номерами строк для каждого типа.

✅ Zero overhead
✅ Zero risk
✅ Easy to maintain with grep/search
❌ Номера строк устаревают

### Option 2: Extract inline functions (Minimal Changes)

Вынести логику в inline функции БЕЗ trait objects:

```rust
// utils.rs или отдельный файл per type

/// DateTime serialization - ALL logic here
#[inline]
pub fn serialize_datetime_to_string<const N: usize>(
    buf: &mut ArrayString<N>,
    dt: &Bound<'_, PyDateTime>,
    field: &FieldDescriptor,
    py: Python<'_>,
) -> PyResult<()> {
    let offset_seconds = dt.get_tzinfo()
        .map(|tz| get_tz_offset_seconds(py, &tz, dt.as_any()))
        .transpose()?;

    if let Some(ref fmt) = field.datetime_format {
        format_datetime_with_strftime(buf, ...);
    } else {
        format_datetime_to_buf(buf, ...);
    }
    Ok(())
}
```

Затем в serialize.rs:
```rust
FieldType::DateTime => {
    let dt = value.downcast::<PyDateTime>().map_err(|_| ...)?;
    let mut buf = ArrayString::<128>::new();
    serialize_datetime_to_string(&mut buf, dt, field, ctx.py)?;
    Ok(PyString::new(ctx.py, &buf).into_any().unbind())
}
```

✅ Zero runtime overhead (inline)
✅ Single source of truth for datetime logic
✅ Tests can test individual functions
❌ Some code changes needed

### Option 3: Macro-based Code Generation

```rust
macro_rules! define_field_handler {
    ($name:ident, $py_type:ty, $error_msg:literal) => {
        #[inline]
        pub fn $name<'py>(
            value: &Bound<'py, PyAny>,
            field: &FieldDescriptor,
        ) -> PyResult<()> {
            if !value.is_instance_of::<$py_type>() {
                return Err(field_error(field, $error_msg));
            }
            Ok(())
        }
    };
}

define_field_handler!(validate_str, PyString, "Not a valid string.");
define_field_handler!(validate_int, PyInt, "Not a valid integer.");
define_field_handler!(validate_bool, PyBool, "Not a valid boolean.");
```

✅ Zero runtime overhead
✅ DRY principle
✅ Compile-time code generation
❌ Macros harder to debug
❌ IDE support worse

## Recommendation

**Option 1 + частично Option 2**:

1. Создать `docs/TYPE_REFERENCE.md` - немедленно помогает навигации
2. Постепенно выносить inline функции для сложных типов (DateTime, Decimal)
3. Не трогать простые типы (Str, Int, Bool) - они и так понятны

## Current Implementation

1. Создан `docs/TYPE_REFERENCE.md` с таблицей маппинга Type → File:Line для быстрого поиска.

2. Реализованы inline helper функции в `utils.rs` для сложных типов:
   - `DateTimeComponents` struct + `extract_datetime_components()` + `serialize_datetime_to_iso()` + `serialize_datetime_with_format()`
   - `format_uuid_to_buf()` для UUID сериализации
   - `DecimalResult` enum + `process_decimal_for_serialization()` для Decimal с валидацией и округлением

Это решает проблему "где сериализуется тип X" без добавления runtime overhead.
Теперь логика DateTime/Decimal/UUID сериализации находится в одном месте (utils.rs), а не дублируется в serialize.rs и serialize_bytes.rs.
