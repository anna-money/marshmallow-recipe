"""
Per-dataclass customization with @mr.options decorator.

This example demonstrates @mr.options decorator for per-dataclass settings:
- naming_case: field name conversion per dataclass
- none_value_handling: None value serialization per dataclass
- decimal_places: decimal precision per dataclass
- Nested dataclasses keep their own settings (NOT inherited)
"""

import dataclasses
import decimal
import uuid

import marshmallow_recipe as mr


# ============================================================
# Pattern 1: naming_case per dataclass
# ============================================================


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


# ============================================================
# Pattern 2: none_value_handling per dataclass
# ============================================================


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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(none_value_handling=mr.NoneValueHandling.IGNORE)
class IgnoreNoneProduct:
    """IGNORE: None values excluded via @mr.options (explicit)."""

    product_name: str
    description: str | None = None


# ============================================================
# Pattern 3: decimal_places per dataclass
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DefaultPrecisionProduct:
    """Default decimal precision (2 places)."""

    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=4)
class HighPrecisionProduct:
    """4 decimal places via @mr.options."""

    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=9)
class VeryHighPrecisionProduct:
    """9 decimal places via @mr.options (for forex/crypto)."""

    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal


# ============================================================
# Pattern 4: Nested dataclasses keep their own settings
# ============================================================


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


if __name__ == "__main__":
    product_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    print("=== Pattern 1: naming_case per dataclass ===")

    # snake_case (default)
    snake_product = SnakeCaseProduct(
        product_id=product_id,
        product_name="Laptop",
        unit_price=decimal.Decimal("999.99"),
    )
    snake_dict = mr.dump(snake_product)
    print(f"SnakeCaseProduct: {list(snake_dict.keys())}")
    # ['product_id', 'product_name', 'unit_price']

    # camelCase via @mr.options
    camel_product = CamelCaseProduct(
        product_id=product_id,
        product_name="Laptop",
        unit_price=decimal.Decimal("999.99"),
    )
    camel_dict = mr.dump(camel_product)
    print(f"CamelCaseProduct: {list(camel_dict.keys())}")
    # ['productId', 'productName', 'unitPrice']

    # PascalCase via @mr.options
    pascal_product = PascalCaseProduct(
        product_id=product_id,
        product_name="Laptop",
        unit_price=decimal.Decimal("999.99"),
    )
    pascal_dict = mr.dump(pascal_product)
    print(f"PascalCaseProduct: {list(pascal_dict.keys())}")
    # ['ProductId', 'ProductName', 'UnitPrice']

    print("✓ Different dataclasses, different naming conventions!")

    print("\n=== Pattern 2: none_value_handling per dataclass ===")

    # Default: IGNORE
    default_product = DefaultNoneProduct(product_name="Laptop", description=None)
    default_dict = mr.dump(default_product)
    print(f"DefaultNoneProduct (IGNORE): 'description' present = {'description' in default_dict}")
    # False - None excluded

    # INCLUDE via @mr.options
    include_product = IncludeNoneProduct(product_name="Laptop", description=None)
    include_dict = mr.dump(include_product)
    print(f"IncludeNoneProduct (INCLUDE): 'description' present = {'description' in include_dict}")
    print(f"  Value: {include_dict['description']}")
    # True - None included

    # Explicit IGNORE via @mr.options
    ignore_product = IgnoreNoneProduct(product_name="Laptop", description=None)
    ignore_dict = mr.dump(ignore_product)
    print(f"IgnoreNoneProduct (IGNORE): 'description' present = {'description' in ignore_dict}")
    # False - None excluded

    print("✓ Different dataclasses, different None handling!")

    print("\n=== Pattern 3: decimal_places per dataclass ===")

    # Default: 2 places
    default_precision = DefaultPrecisionProduct(
        unit_price=decimal.Decimal("999.99567"),
        tax_rate=decimal.Decimal("0.12345"),
    )
    default_dict = mr.dump(default_precision)
    print(f"DefaultPrecisionProduct (2 places):")
    print(f"  unit_price: {default_dict['unit_price']}")
    print(f"  tax_rate: {default_dict['tax_rate']}")

    # 4 places via @mr.options
    high_precision = HighPrecisionProduct(
        unit_price=decimal.Decimal("999.99567"),
        tax_rate=decimal.Decimal("0.12345"),
    )
    high_dict = mr.dump(high_precision)
    print(f"HighPrecisionProduct (4 places):")
    print(f"  unit_price: {high_dict['unit_price']}")
    print(f"  tax_rate: {high_dict['tax_rate']}")

    # 9 places via @mr.options
    very_high_precision = VeryHighPrecisionProduct(
        unit_price=decimal.Decimal("999.99567123"),
        tax_rate=decimal.Decimal("0.12345678901"),
    )
    very_high_dict = mr.dump(very_high_precision)
    print(f"VeryHighPrecisionProduct (9 places):")
    print(f"  unit_price: {very_high_dict['unit_price']}")
    print(f"  tax_rate: {very_high_dict['tax_rate']}")

    print("✓ Different dataclasses, different decimal precision!")

    print("\n=== Pattern 4: Nested dataclasses keep their own settings ===")

    inner = InnerProduct(
        inner_name="Widget",
        inner_price=decimal.Decimal("123.456789"),
    )
    outer = OuterOrder(
        outer_id=product_id,
        outer_total=decimal.Decimal("999.123456"),
        product=inner,
    )

    outer_dict = mr.dump(outer)
    print(f"OuterOrder (camelCase, 4 places):")
    print(f"  Top-level keys: {list(outer_dict.keys())}")
    print(f"  outerTotal: {outer_dict['outerTotal']}")
    # ['outerId', 'outerTotal', 'product']
    # outerTotal: 999.1235 (4 places from @mr.options)

    print(f"\nInnerProduct (snake_case, 2 places):")
    print(f"  Nested keys: {list(outer_dict['product'].keys())}")
    print(f"  inner_price: {outer_dict['product']['inner_price']}")
    # ['inner_name', 'inner_price']
    # inner_price: 123.46 (2 places, NOT 4!)

    assert "outerId" in outer_dict  # camelCase from outer
    assert outer_dict["outerTotal"] == "999.1235"  # 4 places from outer
    assert "inner_name" in outer_dict["product"]  # snake_case from inner (NOT camelCase!)
    assert outer_dict["product"]["inner_price"] == "123.46"  # 2 places from inner (NOT 4!)

    print("✓ Nested dataclasses keep their own @mr.options settings!")

    print("\n=== Summary ===")
    print("@mr.options decorator configures per-dataclass settings:")
    print("✓ naming_case: each dataclass has its own naming convention")
    print("✓ none_value_handling: each dataclass controls its None handling")
    print("✓ decimal_places: each dataclass has its own decimal precision")
    print("✓ Nested dataclasses keep their own settings (NOT inherited)")
