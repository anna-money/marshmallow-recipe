# Value Serialization

The `dump_value` and `load_value` functions allow serializing and deserializing arbitrary Python types, not just dataclasses.

## Basic Usage

```python
import marshmallow_recipe as mr

# Serialize primitive types
dumped = mr.dump_value(int, 42)  # Returns: 42
loaded = mr.load_value(int, 42)  # Returns: 42

# Serialize strings
dumped = mr.dump_value(str, "hello")  # Returns: "hello"
loaded = mr.load_value(str, "hello")  # Returns: "hello"
```

## Collections

```python
import marshmallow_recipe as mr

# Lists
dumped = mr.dump_value(list[int], [1, 2, 3])  # Returns: [1, 2, 3]
loaded = mr.load_value(list[int], [1, 2, 3])  # Returns: [1, 2, 3]

# Dictionaries
dumped = mr.dump_value(dict[str, int], {"a": 1, "b": 2})  # Returns: {"a": 1, "b": 2}
loaded = mr.load_value(dict[str, int], {"a": 1, "b": 2})  # Returns: {"a": 1, "b": 2}

# Sets (serialized as lists)
dumped = mr.dump_value(set[int], {1, 2, 3})  # Returns: [1, 2, 3]
loaded = mr.load_value(set[int], [1, 2, 3])  # Returns: {1, 2, 3}
```

## Complex Types

```python
import dataclasses
import datetime
import decimal
import uuid
import marshmallow_recipe as mr

# Decimals
dumped = mr.dump_value(
    list[decimal.Decimal],
    [decimal.Decimal("1.23"), decimal.Decimal("4.56")]
)  # Returns: ["1.23", "4.56"]

# UUIDs
id = uuid.UUID("12345678-1234-5678-1234-567812345678")
dumped = mr.dump_value(uuid.UUID, id)  # Returns: "12345678-1234-5678-1234-567812345678"

# Datetimes
dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
dumped = mr.dump_value(datetime.datetime, dt)  # Returns: "2024-01-01T12:00:00+00:00"
```

## Nested Dataclasses in Collections

```python
import dataclasses
import marshmallow_recipe as mr

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Holder[T]:
    value: T

# List of dataclasses
items = [Holder(value=1), Holder(value=2), Holder(value=3)]
dumped = mr.dump_value(list[Holder[int]], items)
# Returns: [{"value": 1}, {"value": 2}, {"value": 3}]

loaded = mr.load_value(list[Holder[int]], dumped)
# Returns: [Holder(value=1), Holder(value=2), Holder(value=3)]
```

## Optional Types

```python
import marshmallow_recipe as mr

# Optional values
dumped = mr.dump_value(list[int] | None, None)  # Returns: None
loaded = mr.load_value(list[int] | None, None)  # Returns: None

# Lists with optional elements
dumped = mr.dump_value(list[int | None], [1, None, 3])  # Returns: [1, None, 3]
loaded = mr.load_value(list[int | None], [1, None, 3])  # Returns: [1, None, 3]
```

## When to Use

Use `dump_value`/`load_value` when you need to:
- Serialize collections of primitives or dataclasses
- Work with types that aren't dataclasses directly
- Serialize dictionary values with complex types

**Note:** `dump_value`/`load_value` do NOT accept dataclasses as the root type. For dataclass instances, use the regular `dump`/`load` functions:

```python
# Correct usage
mr.dump(holder_instance)  # For dataclass
mr.dump_value(list[int], [1, 2, 3])  # For non-dataclass types
mr.dump_value(list[Holder[int]], [Holder(value=1)])  # Collections of dataclasses OK

# This will raise ValueError:
mr.dump_value(Holder[int], Holder(value=42))  # Use mr.dump() instead
```
