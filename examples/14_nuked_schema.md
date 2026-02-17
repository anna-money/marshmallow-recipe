# Nuked Schema

Generates a marshmallow Schema for introspection (aiohttp-apispec, OpenAPI), but delegates `load()` and `dump()` to the Rust backend — automatic speedup without any extra effort.

## Basic Usage

```python
import dataclasses

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: int
    name: str
    email: str


schema = mr.nuked.schema(User)

# load/dump work as usual — but run through Rust
user = schema.load({"id": 1, "name": "Alice", "email": "alice@example.com"})
# User(id=1, name='Alice', email='alice@example.com')

data = schema.dump(user)
# {"id": 1, "name": "Alice", "email": "alice@example.com"}

# Schema fields are available for introspection (aiohttp-apispec)
print(schema.fields)
```

## Loading Many Items

```python
schema = mr.nuked.schema(User, many=True)

users = schema.load([
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
])
# [User(id=1, ...), User(id=2, ...)]
```

## With Parameters

```python
import decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    product_name: str
    price: decimal.Decimal


schema = mr.nuked.schema(
    Product,
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
    decimal_places=2,
)

product = schema.load({"productName": "Widget", "price": "9.99"})
# Product(product_name='Widget', price=Decimal('9.99'))
```

## aiohttp-apispec Integration

```python
from aiohttp import web


schema = mr.nuked.schema(User)

# Schema fields drive OpenAPI spec generation
# load/dump run through Rust — speedup is automatic
@docs(summary="Create user")
@request_schema(schema)
async def create_user(request: web.Request) -> web.Response:
    data = await request.json()
    user = schema.load(data)
    ...
```
