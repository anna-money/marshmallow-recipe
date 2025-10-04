# marshmallow-recipe Examples

This directory contains comprehensive examples demonstrating all features of marshmallow-recipe.

## Examples Overview

### 01_basic_usage.py
**Basic serialization and deserialization**
- All supported basic types (str, int, float, bool, decimal, datetime, uuid, enums)
- Simple `mr.dump()` and `mr.load()` operations
- Optional types and default values
- Working with many objects (`load_many`, `dump_many`)
- Schema generation

**Run:** `python examples/01_basic_usage.py`

---

### 02_nested_and_collections.py
**Nested dataclasses and collections**
- Nested dataclasses (Address, PhoneNumber in Customer)
- Lists, sets, frozensets, tuples
- Dictionaries with complex keys/values (e.g., `dict[datetime.date, decimal.Decimal]`)
- Optional nested structures
- Collections of nested dataclasses

**Run:** `python examples/02_nested_and_collections.py`

---

### 03_field_customization.py
**Field-level customization**
- Custom field names: `mr.meta(name="customName")`
- String transformations: `mr.str_meta(strip_whitespaces=True, post_load=func)`
- Decimal precision: `mr.decimal_meta(places=N)`
- Field validation: lambda validators and `mr.regexp_validate()`
- Collection item validation: `mr.list_meta(validate_item=func)`
- Using `Annotated` type hints

**Run:** `python examples/03_field_customization.py`

---

### 04_naming_cases.py
**Naming case conventions**
- `@mr.options(naming_case=mr.CAMEL_CASE)` for camelCase
- `@mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)` for PascalCase
- `@mr.options(naming_case=mr.UPPER_SNAKE_CASE)` for UPPER_SNAKE_CASE
- Per-call naming case override: `mr.dump(obj, naming_case=...)`
- Nested dataclasses keep their own conventions
- Reusable serialization wrappers for external APIs

**Run:** `python examples/04_naming_cases.py`

---

### 05_patch_operations.py
**PATCH operations with mr.MISSING**
- Using `mr.MISSING` to distinguish null from missing fields
- PATCH vs PUT operations
- Partial updates with `mr.MISSING` as default value
- Combining with `none_value_handling=INCLUDE`
- Real-world PATCH operation patterns from production code

**Run:** `python examples/05_patch_operations.py`

---

### 06_generics.py
**Generic types (Generic[T])**
- Basic `Generic[T]` usage
- Generic with `frozen=True`/`slots=True` requires explicit type
- Nested generics: `Generic[Other[T]]`
- Generic inheritance
- Reusing Generic with different type arguments
- PagedResponse, Result, ApiResponse patterns

**Run:** `python examples/06_generics.py`

---

### 08_global_parameters.py
**Global runtime parameters**
- All three global parameters: `naming_case`, `none_value_handling`, `decimal_places`
- Runtime parameters passed to `load()`, `dump()`, `schema()`
- Runtime parameters override `@mr.options` decorator
- Schema caching per parameter combination

**Run:** `python examples/08_global_parameters.py`

---

### 09_advanced_patterns.py
**Advanced patterns and combining features**
- BaseModel pattern with `dump()`/`load()`/`schema()` methods
- Cyclic/self-referencing structures (TreeNode, Comment with replies)
- `@mr.pre_load` hooks for data transformation
- `@mr.options(decimal_places=N)` for global decimal precision
- `@mr.options(none_value_handling=INCLUDE)` for including None values
- Combining all features together

**Run:** `python examples/09_advanced_patterns.py`

---

### 10_advanced_features.py
**Advanced features and edge cases**
- `add_pre_load()` for programmatic hook addition
- `get_validation_field_errors()` for structured error handling
- `datetime_meta(format=...)` for custom datetime formats
- `validate()` helper function
- `collections.abc` types (Sequence, Set, Mapping)
- `NewType` support

**Run:** `python examples/10_advanced_features.py`

---

## Quick Reference

### Basic Operations
```python
import marshmallow_recipe as mr

# Serialize
data_dict = mr.dump(obj)

# Deserialize
obj = mr.load(MyClass, data_dict)

# Many objects
objs = mr.load_many(MyClass, list_of_dicts)
dicts = mr.dump_many(list_of_objs)
```

### Field Customization
```python
from typing import Annotated

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Model:
    # Custom name
    field1: Annotated[str, mr.meta(name="customName")]

    # String transformation
    field2: Annotated[str, mr.str_meta(strip_whitespaces=True)]

    # Decimal precision
    field3: Annotated[decimal.Decimal, mr.decimal_meta(places=2)]

    # Validation
    field4: Annotated[str, mr.str_meta(validate=mr.regexp_validate(r"^\d+$"))]
```

### Class-Level Options
```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
    decimal_places=2
)
class Model:
    user_id: int  # Serialized as "userId"
    balance: decimal.Decimal  # Serialized with 2 decimal places
    note: str | None = None  # None included in output
```

### PATCH Operations
```python
@dataclasses.dataclass
class UpdateModel:
    field1: str = mr.MISSING
    field2: int = mr.MISSING

# Only provided fields are in output
update = UpdateModel(field1="new_value")
mr.dump(update)  # {"field1": "new_value"} - field2 excluded
```

### Generic Types
```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Container(Generic[T]):
    value: T

# Must provide type for frozen/slots
obj = Container[int](value=42)
data = mr.dump(Container[int], obj)
loaded = mr.load(Container[int], data)
```

## Running All Examples

```bash
cd /Users/pliner/Source/marshmallow-recipe
python examples/01_basic_usage.py
python examples/02_nested_and_collections.py
python examples/03_field_customization.py
python examples/04_naming_cases.py
python examples/05_patch_operations.py
python examples/06_generics.py
python examples/08_global_parameters.py
python examples/09_advanced_patterns.py
python examples/10_advanced_features.py
```

## See Also

- [README.md](../README.md) - Main project documentation
- [tests/](../tests/) - Comprehensive test suite with more examples
- [context7.json](../context7.json) - AI context configuration for this library
