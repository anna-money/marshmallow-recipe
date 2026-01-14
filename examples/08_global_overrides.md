# Global Overrides

Runtime parameters passed to `load()`, `dump()`, and `schema()` to override default behaviour.

## naming_case at Runtime

Change field name conversion at runtime without modifying the dataclass:

```python
import dataclasses
import decimal
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    product_id: uuid.UUID
    product_name: str
    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal


product = Product(
    product_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    product_name="Laptop",
    unit_price=decimal.Decimal("999.99"),
    tax_rate=decimal.Decimal("0.12"),
)

# Default: snake_case
default_dump = mr.dump(product)
# {'product_id': '...', 'product_name': 'Laptop', 'unit_price': '999.99', 'tax_rate': '0.12'}

# Runtime: camelCase
camel_dump = mr.dump(product, naming_case=mr.CAMEL_CASE)
# {'productId': '...', 'productName': 'Laptop', 'unitPrice': '999.99', 'taxRate': '0.12'}

# Runtime: PascalCase
pascal_dump = mr.dump(product, naming_case=mr.CAPITAL_CAMEL_CASE)
# {'ProductId': '...', 'ProductName': 'Laptop', 'UnitPrice': '999.99', 'TaxRate': '0.12'}

# Load with naming_case
loaded_from_camel = mr.load(Product, camel_dump, naming_case=mr.CAMEL_CASE)
```

## none_value_handling at Runtime

Control None value serialisation at runtime:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    product_name: str
    description: str | None = None


product = Product(product_name="Laptop", description=None)

# Default: IGNORE (None values excluded)
default_dump = mr.dump(product)
# {'product_name': 'Laptop'}
# 'description' not present

# Runtime: INCLUDE
include_dump = mr.dump(product, none_value_handling=mr.NoneValueHandling.INCLUDE)
# {'product_name': 'Laptop', 'description': None}
# 'description' present with None value

# Load with none_value_handling
loaded_include = mr.load(Product, include_dump, none_value_handling=mr.NoneValueHandling.INCLUDE)
```

## decimal_places at Runtime

Control decimal precision validation at runtime:

```python
product = Product(
    product_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    product_name="Laptop",
    unit_price=decimal.Decimal("999.99"),
    tax_rate=decimal.Decimal("0.12"),
)

# Default: validates at most 2 decimal places
default_dump = mr.dump(product)
# {'unit_price': '999.99', 'tax_rate': '0.12'}

# Runtime: validates at most 4 decimal places (allows more precision)
product_4dp = Product(
    product_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    product_name="Laptop",
    unit_price=decimal.Decimal("999.9957"),
    tax_rate=decimal.Decimal("0.1235"),
)
four_places = mr.dump(product_4dp, decimal_places=4)
# {'unit_price': '999.9957', 'tax_rate': '0.1235'}

# Runtime: validates at most 9 decimal places (high precision)
product_9dp = Product(
    product_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    product_name="Laptop",
    unit_price=decimal.Decimal("999.995670000"),
    tax_rate=decimal.Decimal("0.123450000"),
)
nine_places = mr.dump(product_9dp, decimal_places=9)
# {'unit_price': '999.99567', 'tax_rate': '0.12345'}

# If value has more decimal places than allowed, ValidationError is raised
```

## Combining Multiple Overrides

All runtime parameters can be used together:

```python
result = mr.dump(
    product_4dp,
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
    decimal_places=4,
)
# {
#     'productId': '...',
#     'productName': 'Laptop',
#     'unitPrice': '999.9957',
#     'taxRate': '0.1235',
#     'description': None
# }
```

## Use Case: Multiple API Integrations

Different APIs may require different formats:

```python
# Internal API: snake_case, 2 decimal places
internal_data = mr.dump(product)

# External REST API: camelCase, 4 decimal places
external_data = mr.dump(
    product_4dp,
    naming_case=mr.CAMEL_CASE,
    decimal_places=4,
)

# GraphQL API: PascalCase, include None
graphql_data = mr.dump(
    product,
    naming_case=mr.CAPITAL_CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
)

# All from the same dataclass, different serialisation formats!
```

## Schema Generation with Overrides

Schemas are cached separately for each parameter combination:

```python
# Different schemas for different parameters
schema_default = mr.schema(Product)
schema_camel = mr.schema(Product, naming_case=mr.CAMEL_CASE)
schema_4dp = mr.schema(Product, decimal_places=4)

# Each combination gets its own cached schema
# schema_default is not schema_camel
```

## Available Parameters

All three functions accept these parameters:

- `naming_case` - `mr.CAMEL_CASE`, `mr.CAPITAL_CAMEL_CASE`, `mr.UPPER_SNAKE_CASE`, or `None` (default)
- `none_value_handling` - `mr.NoneValueHandling.INCLUDE` or `mr.NoneValueHandling.IGNORE` (default)
- `decimal_places` - Integer or `None` (default 2) - validates max decimal places

These can be passed to:
- `mr.dump(obj, ...)` - Serialisation
- `mr.load(cls, data, ...)` - Deserialisation
- `mr.schema(cls, ...)` - Schema generation
