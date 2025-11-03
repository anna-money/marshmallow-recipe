# Value Serialization

marshmallow-recipe supports serialization of standalone values (collections and primitives) without requiring a dataclass wrapper through `load_value()` and `dump_value()`.

## Basic Usage

```python
import marshmallow_recipe as mr

# List serialization
data = [1, 2, 3]
dumped = mr.dump_value(data)  # [1, 2, 3]
loaded = mr.load_value(list[int], dumped)  # [1, 2, 3]

# Dict serialization
data = {"a": 1, "b": 2}
dumped = mr.dump_value(data)  # {"a": 1, "b": 2}
loaded = mr.load_value(dict[str, int], dumped)  # {"a": 1, "b": 2}

# Set serialization
data = {1, 2, 3}
dumped = mr.dump_value(data)  # [1, 2, 3] (unordered)
loaded = mr.load_value(set[int], dumped)  # {1, 2, 3}
```

## Complex Types

For collections containing complex types (dataclasses, decimals, UUIDs, etc.), you must specify the type explicitly in `dump_value()`:

```python
import dataclasses
import decimal
import marshmallow_recipe as mr

@dataclasses.dataclass
class User:
    name: str
    age: int

# List with dataclasses
data = [User(name="Alice", age=30), User(name="Bob", age=25)]
dumped = mr.dump_value(list[User], data)
# [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
loaded = mr.load_value(list[User], dumped)
# [User(name='Alice', age=30), User(name='Bob', age=25)]

# List with Decimal
data = [decimal.Decimal("1.23"), decimal.Decimal("4.56")]
dumped = mr.dump_value(list[decimal.Decimal], data)  # ["1.23", "4.56"]
loaded = mr.load_value(list[decimal.Decimal], dumped)
# [Decimal('1.23'), Decimal('4.56')]
```

## Nested Collections

```python
import marshmallow_recipe as mr

# Nested lists
data = [[1, 2], [3, 4]]
dumped = mr.dump_value(data)  # [[1, 2], [3, 4]]
loaded = mr.load_value(list[list[int]], dumped)  # [[1, 2], [3, 4]]

# Dict with list values
data = {"a": [1, 2], "b": [3, 4]}
dumped = mr.dump_value(data)  # {"a": [1, 2], "b": [3, 4]}
loaded = mr.load_value(dict[str, list[int]], dumped)
# {"a": [1, 2], "b": [3, 4]}
```

## Optional Values

```python
import marshmallow_recipe as mr

# List with optional elements
data = [1, None, 3]
dumped = mr.dump_value(data)  # [1, None, 3]
loaded = mr.load_value(list[int | None], dumped)  # [1, None, 3]

# Optional collection
data: list[int] | None = None
dumped = mr.dump_value(data)  # None
loaded = mr.load_value(list[int] | None, dumped)  # type: ignore
# None
```

## When to Use value vs dataclass Methods

Use **`load_value()`/`dump_value()`** when:
- Serializing standalone collections (lists, dicts, sets)
- Working with APIs that return raw lists or primitive values
- No schema generation is needed

Use **`load()`/`dump()`** when:
- Serializing dataclass instances
- Need schema introspection via `schema()`
- Working with structured data

## Type Inference Limitations

For simple types (int, str, bool), `dump_value()` can infer types automatically:

```python
import marshmallow_recipe as mr

data = [1, 2, 3]
dumped = mr.dump_value(data)  # Works without type
```

For complex types, explicit type specification is required:

```python
import dataclasses
import marshmallow_recipe as mr

@dataclasses.dataclass
class User:
    name: str

data = [User(name="Alice")]
# REQUIRED: explicit type for complex nested types
dumped = mr.dump_value(list[User], data)
```

## Implementation Details

Under the hood, `load_value()` and `dump_value()` create a cached wrapper dataclass with a single `value` field, then use the standard `load()`/`dump()` machinery. This ensures consistent behavior with regular dataclass serialization.
