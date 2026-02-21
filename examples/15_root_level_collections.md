# Root-Level Collections (Nuked)

Using `mr.nuked.dump()` and `mr.nuked.load()` with root-level collections of primitive types, without wrapping in a dataclass.

## Basic Primitives

```python
import datetime
import decimal
import uuid

import marshmallow_recipe as mr

# dict[str, T] with various primitive types
data = {"key1": 42, "key2": 7}
dumped = mr.nuked.dump(dict[str, int], data)
loaded = mr.nuked.load(dict[str, int], dumped)
assert loaded == data

# datetime values
dates = {"event": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}
dumped = mr.nuked.dump(dict[str, datetime.datetime], dates)
# {"event": "2024-01-15T10:30:00+00:00"}
loaded = mr.nuked.load(dict[str, datetime.datetime], dumped)
assert loaded == dates

# decimal values
prices = {"item1": decimal.Decimal("9.99"), "item2": decimal.Decimal("19.99")}
dumped = mr.nuked.dump(dict[str, decimal.Decimal], prices)
loaded = mr.nuked.load(dict[str, decimal.Decimal], dumped)
assert loaded == prices

# uuid values
ids = {"user": uuid.UUID("550e8400-e29b-41d4-a716-446655440000")}
dumped = mr.nuked.dump(dict[str, uuid.UUID], ids)
loaded = mr.nuked.load(dict[str, uuid.UUID], dumped)
assert loaded == ids
```

## Nested Collections

```python
# dict[str, list[int]]
data = {"scores": [95, 87, 92], "grades": [100, 88]}
dumped = mr.nuked.dump(dict[str, list[int]], data)
loaded = mr.nuked.load(dict[str, list[int]], dumped)
assert loaded == data

# dict[str, dict[str, int]]
nested = {"group1": {"a": 1}, "group2": {"b": 2}}
dumped = mr.nuked.dump(dict[str, dict[str, int]], nested)
loaded = mr.nuked.load(dict[str, dict[str, int]], dumped)
assert loaded == nested
```

## Enums and Dataclasses

```python
import dataclasses
import enum


class Status(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    street: str
    city: str


# dict[str, Enum]
statuses = {"user1": Status.ACTIVE, "user2": Status.INACTIVE}
dumped = mr.nuked.dump(dict[str, Status], statuses)
loaded = mr.nuked.load(dict[str, Status], dumped)
assert loaded == statuses

# dict[str, Dataclass]
addresses = {"home": Address(street="Main St", city="NYC")}
dumped = mr.nuked.dump(dict[str, Address], addresses)
loaded = mr.nuked.load(dict[str, Address], dumped)
assert loaded == addresses
```
