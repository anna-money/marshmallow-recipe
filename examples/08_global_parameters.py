"""
Global parameters (runtime overrides) in marshmallow-recipe.

This example demonstrates runtime parameters passed to load/dump/schema:
- naming_case: field name conversion at runtime
- none_value_handling: None value serialization at runtime
- decimal_places: decimal precision at runtime
"""

import dataclasses
import decimal
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    """Product for demonstrating runtime parameters."""

    product_id: uuid.UUID
    product_name: str
    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal
    description: str | None = None


if __name__ == "__main__":
    product = Product(
        product_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        product_name="Laptop",
        unit_price=decimal.Decimal("999.99567"),
        tax_rate=decimal.Decimal("0.12345"),
        description=None,
    )

    print("=== Pattern 1: naming_case at runtime ===")

    # Default: snake_case
    default_dump = mr.dump(product)
    print(f"Default (snake_case): {list(default_dump.keys())}")
    # ['product_id', 'product_name', 'unit_price', 'tax_rate']

    # Runtime: camelCase
    camel_dump = mr.dump(product, naming_case=mr.CAMEL_CASE)
    print(f"camelCase: {list(camel_dump.keys())}")
    # ['productId', 'productName', 'unitPrice', 'taxRate']

    # Runtime: PascalCase
    pascal_dump = mr.dump(product, naming_case=mr.CAPITAL_CAMEL_CASE)
    print(f"PascalCase: {list(pascal_dump.keys())}")
    # ['ProductId', 'ProductName', 'UnitPrice', 'TaxRate']

    # Load with naming_case
    loaded_from_camel = mr.load(Product, camel_dump, naming_case=mr.CAMEL_CASE)
    assert loaded_from_camel == product
    print("✓ Same dataclass, different naming at runtime!")

    print("\n=== Pattern 2: none_value_handling at runtime ===")

    # Default: IGNORE (None values excluded)
    default_dump = mr.dump(product)
    print(f"Default (IGNORE): 'description' present = {'description' in default_dump}")
    # False - None excluded

    # Runtime: INCLUDE
    include_dump = mr.dump(product, none_value_handling=mr.NoneValueHandling.INCLUDE)
    print(f"INCLUDE: 'description' present = {'description' in include_dump}")
    print(f"  Value: {include_dump['description']}")
    # True - None included

    # Load with none_value_handling
    loaded_include = mr.load(Product, include_dump, none_value_handling=mr.NoneValueHandling.INCLUDE)
    assert loaded_include == product
    print("✓ Same dataclass, different None handling at runtime!")

    print("\n=== Pattern 3: decimal_places at runtime ===")

    # Default: 2 decimal places (marshmallow default)
    default_dump = mr.dump(product)
    print(f"Default (2 places):")
    print(f"  unit_price: {default_dump['unit_price']}")
    print(f"  tax_rate: {default_dump['tax_rate']}")

    # Runtime: 2 decimal places (explicit)
    two_places = mr.dump(product, decimal_places=2)
    print(f"decimal_places=2:")
    print(f"  unit_price: {two_places['unit_price']}")
    print(f"  tax_rate: {two_places['tax_rate']}")

    # Runtime: 4 decimal places
    four_places = mr.dump(product, decimal_places=4)
    print(f"decimal_places=4:")
    print(f"  unit_price: {four_places['unit_price']}")
    print(f"  tax_rate: {four_places['tax_rate']}")

    # Runtime: 9 decimal places (high precision)
    nine_places = mr.dump(product, decimal_places=9)
    print(f"decimal_places=9:")
    print(f"  unit_price: {nine_places['unit_price']}")
    print(f"  tax_rate: {nine_places['tax_rate']}")

    print("✓ Same dataclass, different decimal precision at runtime!")

    print("\n=== Summary ===")
    print("Global/runtime parameters can be passed to load(), dump(), schema():")
    print("✓ naming_case: change field names at runtime")
    print("✓ none_value_handling: control None serialization at runtime")
    print("✓ decimal_places: control decimal precision at runtime")
