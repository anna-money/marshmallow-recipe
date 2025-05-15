# marshmallow-recipe

[![PyPI version](https://badge.fury.io/py/marshmallow-recipe.svg)](https://badge.fury.io/py/marshmallow-recipe)
[![Python Versions](https://img.shields.io/pypi/pyversions/marshmallow-recipe.svg)](https://pypi.org/project/marshmallow-recipe/)

Library for convenient serialization/deserialization of Python dataclasses using marshmallow.

Originally developed as an abstraction layer over marshmallow to facilitate migration from v2 to v3 for codebases with extensive dataclass usage, 
this library has evolved into a powerful tool offering a more concise approach to serialization. 
It can be seamlessly integrated into any codebase, providing the following benefits:

1. Automatic schema generation: Marshmallow schemas are generated and cached automatically, while still being accessible when needed
2. Comprehensive Generics support with full nesting and inheritance capabilities
3. Flexible field configuration through `dataclass.field(meta)` or `Annotated[T, meta]`
4. Customizable case formatting support, including built-in `camelCase` and `CamelCase`, via dataclass decorators
5. Configurable None value handling through dataclass decorators
6. PATCH operation support via mr.MISSING value

## Supported Types

### Simple Types
- text
  - `str`
- boolean
  - `bool`
- numeric
  - `int`
  - `float`
  - `decimal.Decimal` (precision: 2 decimal places by default)
- date and time
  - `datetime.datetime`
  - `datetime.date`
  - `datetime.time`
- UUID
  - `uuid.UUID`
- enum
  - `enum.StrEnum`
  - `enum.IntEnum`

### Collection Types
- sequences
  - `tuple[T, ...]` (homogeneous tuples only)
  - `Sequence[T]`
  - `list[T]`
  - `List[T]`
- sets
  - `set[T]`
  - `Set[T]`
  - `frozenset[T]`
- mappings
  - `dict[TKey, TValue]`
  - `Dict[TKey, TValue]`
  - `Mapping[TKey, TValue]`

### Advanced Types
- nullable types
  - `T | None`
  - `typing.Optional[T]`
  - `typing.Union[T, None]`
- generic types
  - `typing.TypeVar`
  - `typing._GenericAlias`
  - `types.GenericAlias`
- meta types
  - `typing.Annotated[T, _]`
- special types
  - `typing.Any`
  - `typing.NewType(_, T)`


## Examples
### Base scenario

```python
import dataclasses
import datetime
import uuid

import marshmallow_recipe as mr

@dataclasses.dataclass(frozen=True)
class Entity:
    id: uuid.UUID
    created_at: datetime.datetime
    comment: str | None

entity = Entity(
    id=uuid.uuid4(),
    created_at=datetime.datetime.now(tz=datetime.UTC),
    comment=None,
 )

# dumps the dataclass instance to a dict
serialized = mr.dump(entity) 

# deserializes a dict to the dataclass instance
loaded = mr.load(Entity, serialized)

assert loaded == entity

# provides a generated marshmallow schema for the dataclass
marshmallow_schema = mr.schema(Entity)
```

### Configuration

```python
import dataclasses
import datetime
import decimal

import marshmallow_recipe as mr

from typing import Annotated


@dataclasses.dataclass(frozen=True)
class ConfiguredFields:
    with_custom_name: str = dataclasses.field(metadata=mr.meta(name="alias"))
    strip_whitespaces: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True))
    with_post_load: str = dataclasses.field(metadata=mr.str_meta(post_load=lambda x: x.replace("-", "")))
    with_validation: decimal.Decimal = dataclasses.field(metadata=mr.meta(validate=lambda x: x != 0))
    decimal_two_places_by_default: decimal.Decimal  # Note: 2 decimal places by default
    decimal_any_places: decimal.Decimal = dataclasses.field(metadata=mr.decimal_metadata(places=None))
    decimal_three_places: decimal.Decimal = dataclasses.field(metadata=mr.decimal_metadata(places=3))
    decimal_as_number: decimal.Decimal = dataclasses.field(metadata=mr.decimal_metadata(as_string=False))
    nullable_with_custom_format: datetime.date | None = dataclasses.field(metadata=mr.datetime_meta(format="%Y%m%d"), default=None)
    with_default_factory: str = dataclasses.field(default_factory=lambda: "42")


@dataclasses.dataclass(frozen=True)
class AnnotatedFields:
    with_post_load: Annotated[str, mr.str_meta(post_load=lambda x: x.replace("-", ""))]
    decimal_three_places: Annotated[decimal.Decimal, mr.decimal_metadata(places=3)]


@dataclasses.dataclass(frozen=True)
class AnnotatedListItem:
    nullable_value: list[Annotated[str, mr.str_meta(strip_whitespaces=True)]] | None
    value_with_nullable_item: list[Annotated[str | None, mr.str_meta(strip_whitespaces=True)]]


@dataclasses.dataclass(frozen=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class NoneValueFieldIncluded:
    nullable_value: str | None

    
@dataclasses.dataclass(frozen=True)
@mr.options(none_value_handling=mr.NoneValueHandling.IGNORE)
class NoneValueFieldExcluded:
    nullable_value: str | None

    
@dataclasses.dataclass(frozen=True)
@mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)
class UpperCamelCaseExcluded:
    naming_case_applied: str  # serialized to `NamingCaseApplied`
    naming_case_ignored: str = dataclasses.field(metadata=mr.meta(name="alias"))  # serialized to `alias`

    
@dataclasses.dataclass(frozen=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class LowerCamelCaseExcluded:
    naming_case_applied: str  # serialized to `namingCaseApplied`


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DataClass:
    str_field: str

data = dict(StrField="foobar")
loaded = mr.load(DataClass, data, naming_case=mr.CAPITAL_CAMEL_CASE)
dumped = mr.dump(loaded, naming_case=mr.CAPITAL_CAMEL_CASE)
```

### Update API

```python
import decimal
import dataclasses

import marshmallow_recipe as mr

@dataclasses.dataclass(frozen=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class CompanyUpdateData:
    name: str = mr.MISSING
    annual_turnover: decimal.Decimal | None = mr.MISSING

company_update_data = CompanyUpdateData(name="updated name")
dumped = mr.dump(company_update_data)
assert dumped == {"name": "updated name"}  # Note: no "annual_turnover" here

loaded = mr.load(CompanyUpdateData, {"name": "updated name"})
assert loaded.name == "updated name"
assert loaded.annual_turnover is mr.MISSING

loaded = mr.load(CompanyUpdateData, {"annual_turnover": None})
assert loaded.name is mr.MISSING
assert loaded.annual_turnover is None
```

### Generics

Everything works automatically, except for one case. Dump operation of a generic dataclass with `frozen=True` or/and `slots=True` requires an explicitly specified subscripted generic type as first `cls` argument of `dump` and `dump_many` methods.

```python
import dataclasses
from typing import Generic, TypeVar

import marshmallow_recipe as mr

T = TypeVar("T")


@dataclasses.dataclass()
class RegularGeneric(Generic[T]):
    value: T

mr.dump(RegularGeneric[int](value=123))  # it works without explicit cls specification


@dataclasses.dataclass(slots=True)
class SlotsGeneric(Generic[T]):
    value: T

mr.dump(SlotsGeneric[int], SlotsGeneric[int](value=123))  # cls required for slots=True generic

@dataclasses.dataclass(frozen=True)
class FrozenGeneric(Generic[T]):
    value: T

mr.dump(FrozenGeneric[int], FrozenGeneric[int](value=123))  # cls required for frozen=True generic


@dataclasses.dataclass(slots=True, frozen=True)
class SlotsFrozenNonGeneric(FrozenGeneric[int]):
    pass

mr.dump(SlotsFrozenNonGeneric(value=123))  # cls not required for non-generic
```
