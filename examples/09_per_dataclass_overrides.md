# Per-Dataclass Overrides

Using `@mr.options` decorator to configure settings for individual dataclasses.

## naming_case per Dataclass

Each dataclass can have its own naming convention:

```python
import dataclasses
import decimal
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SnakeCaseProduct:
    """Default snake_case naming."""

    product_id: uuid.UUID
    product_name: str
    unit_price: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class CamelCaseProduct:
    """camelCase naming via @mr.options."""

    product_id: uuid.UUID
    product_name: str
    unit_price: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)
class PascalCaseProduct:
    """PascalCase naming via @mr.options."""

    product_id: uuid.UUID
    product_name: str
    unit_price: decimal.Decimal


product_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

# snake_case (default)
snake_product = SnakeCaseProduct(
    product_id=product_id,
    product_name="Laptop",
    unit_price=decimal.Decimal("999.99"),
)
snake_dict = mr.dump(snake_product)
# {'product_id': '...', 'product_name': 'Laptop', 'unit_price': '999.99'}

# camelCase via @mr.options
camel_product = CamelCaseProduct(
    product_id=product_id,
    product_name="Laptop",
    unit_price=decimal.Decimal("999.99"),
)
camel_dict = mr.dump(camel_product)
# {'productId': '...', 'productName': 'Laptop', 'unitPrice': '999.99'}

# PascalCase via @mr.options
pascal_product = PascalCaseProduct(
    product_id=product_id,
    product_name="Laptop",
    unit_price=decimal.Decimal("999.99"),
)
pascal_dict = mr.dump(pascal_product)
# {'ProductId': '...', 'ProductName': 'Laptop', 'UnitPrice': '999.99'}
```

## none_value_handling per Dataclass

Control None value handling per dataclass:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DefaultNoneProduct:
    """Default: None values excluded (IGNORE)."""

    product_name: str
    description: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class IncludeNoneProduct:
    """INCLUDE: None values included via @mr.options."""

    product_name: str
    description: str | None = None


# Default: IGNORE
default_product = DefaultNoneProduct(product_name="Laptop", description=None)
default_dict = mr.dump(default_product)
# {'product_name': 'Laptop'}
# 'description' not present

# INCLUDE via @mr.options
include_product = IncludeNoneProduct(product_name="Laptop", description=None)
include_dict = mr.dump(include_product)
# {'product_name': 'Laptop', 'description': None}
# 'description' present with None
```

## decimal_places per Dataclass

Different dataclasses can have different decimal precision validation:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DefaultPrecisionProduct:
    """Default decimal precision validation (max 2 places)."""

    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=4)
class HighPrecisionProduct:
    """Max 4 decimal places via @mr.options."""

    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=9)
class VeryHighPrecisionProduct:
    """Max 9 decimal places via @mr.options (for forex/crypto)."""

    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal


# Default: validates at most 2 places
default_precision = DefaultPrecisionProduct(
    unit_price=decimal.Decimal("999.99"),
    tax_rate=decimal.Decimal("0.12"),
)
default_dict = mr.dump(default_precision)
# {'unit_price': '999.99', 'tax_rate': '0.12'}

# 4 places via @mr.options
high_precision = HighPrecisionProduct(
    unit_price=decimal.Decimal("999.9957"),
    tax_rate=decimal.Decimal("0.1235"),
)
high_dict = mr.dump(high_precision)
# {'unit_price': '999.9957', 'tax_rate': '0.1235'}

# 9 places via @mr.options
very_high_precision = VeryHighPrecisionProduct(
    unit_price=decimal.Decimal("999.995671"),
    tax_rate=decimal.Decimal("0.123456789"),
)
very_high_dict = mr.dump(very_high_precision)
# {'unit_price': '999.995671', 'tax_rate': '0.123456789'}

# If value exceeds max places, ValidationError is raised
# DefaultPrecisionProduct(unit_price=decimal.Decimal("999.999"), ...)  # Error!
```

## Nested Dataclasses Keep Their Own Settings

**Important:** Nested dataclasses maintain their own `@mr.options` settings. Settings are **not inherited**:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class InnerProduct:
    """Nested product WITHOUT @mr.options (default settings)."""

    inner_name: str
    inner_price: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    decimal_places=4,
)
class OuterOrder:
    """Outer order WITH @mr.options."""

    outer_id: uuid.UUID
    outer_total: decimal.Decimal
    product: InnerProduct  # Nested keeps its own settings!


inner = InnerProduct(
    inner_name="Widget",
    inner_price=decimal.Decimal("123.46"),  # Max 2 places (default)
)
outer = OuterOrder(
    outer_id=uuid.uuid4(),
    outer_total=decimal.Decimal("999.1235"),  # Max 4 places
    product=inner,
)

outer_dict = mr.dump(outer)
# {
#     'outerId': '...',              # camelCase from outer
#     'outerTotal': '999.1235',      # 4 places from outer
#     'product': {
#         'inner_name': 'Widget',    # snake_case from inner (NOT camelCase!)
#         'inner_price': '123.46'    # 2 places from inner (NOT 4!)
#     }
# }
```

## Combining Multiple Options

All options can be combined in one decorator:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
    decimal_places=4,
)
class FullyConfiguredProduct:
    """Product with all options configured."""

    product_name: str
    unit_price: decimal.Decimal
    description: str | None = None


product = FullyConfiguredProduct(
    product_name="Laptop",
    unit_price=decimal.Decimal("999.9957"),  # Max 4 places
    description=None,
)

product_dict = mr.dump(product)
# {
#     'productName': 'Laptop',        # camelCase
#     'unitPrice': '999.9957',        # 4 places
#     'description': None             # None included
# }
```

## Use Case: Domain Models

Different domain models can have appropriate conventions:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class ExternalApiModel:
    """For external REST API (camelCase)."""
    pass


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)
class GraphQLModel:
    """For GraphQL API (PascalCase)."""
    pass


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class InternalModel:
    """For internal use (snake_case)."""
    pass


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=9)
class FinancialModel:
    """For financial calculations (high precision)."""
    pass
```

## Available Options

The `@mr.options` decorator accepts:

- `naming_case` - `mr.CAMEL_CASE`, `mr.CAPITAL_CAMEL_CASE`, `mr.UPPER_SNAKE_CASE`, or `None`
- `none_value_handling` - `mr.NoneValueHandling.INCLUDE` or `mr.NoneValueHandling.IGNORE`
- `decimal_places` - Integer or `None` (validates max decimal places)

These settings:
- Apply to the dataclass and its serialisation/deserialisation
- Are **not inherited** by nested dataclasses
- Can be overridden by runtime parameters (see [08_global_overrides.md](08_global_overrides.md))
