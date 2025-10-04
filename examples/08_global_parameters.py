"""
Global parameters (runtime overrides) in marshmallow-recipe.

This example demonstrates:
- All global parameters: naming_case, none_value_handling, decimal_places
- Passing parameters to load/dump/schema at runtime
- Runtime parameters override @mr.options decorator
- Using different parameters for same dataclass
"""

import dataclasses
import decimal
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    """Product without any @mr.options."""

    product_id: uuid.UUID
    product_name: str
    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal
    description: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.IGNORE,
    decimal_places=2,
)
class ConfiguredProduct:
    """Product with @mr.options configuration."""

    product_id: uuid.UUID
    product_name: str
    unit_price: decimal.Decimal
    tax_rate: decimal.Decimal
    description: str | None = None


if __name__ == "__main__":
    print("=== Global parameters overview ===")
    print("Three global parameters can be passed to load/dump/schema:")
    print("1. naming_case - controls field name conversion")
    print("2. none_value_handling - controls None value serialization")
    print("3. decimal_places - controls decimal precision")
    print()

    product = Product(
        product_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        product_name="Laptop",
        unit_price=decimal.Decimal("999.99567"),
        tax_rate=decimal.Decimal("0.12345"),
        description=None,
    )

    # ============================================================
    # Parameter 1: naming_case
    # ============================================================

    print("=== 1. naming_case (runtime) ===")

    # Default: snake_case
    default_dump = mr.dump(product)
    print(f"Default (snake_case): {list(default_dump.keys())}")
    # ['product_id', 'product_name', 'unit_price', 'tax_rate']

    # Runtime override: camelCase
    camel_dump = mr.dump(product, naming_case=mr.CAMEL_CASE)
    print(f"camelCase: {list(camel_dump.keys())}")
    # ['productId', 'productName', 'unitPrice', 'taxRate']

    # Runtime override: PascalCase
    pascal_dump = mr.dump(product, naming_case=mr.CAPITAL_CAMEL_CASE)
    print(f"PascalCase: {list(pascal_dump.keys())}")
    # ['ProductId', 'ProductName', 'UnitPrice', 'TaxRate']

    # Load with naming_case
    loaded_from_camel = mr.load(Product, camel_dump, naming_case=mr.CAMEL_CASE)
    assert loaded_from_camel == product
    print("✓ naming_case works in both load and dump")

    # ============================================================
    # Parameter 2: none_value_handling
    # ============================================================

    print("\n=== 2. none_value_handling (runtime) ===")

    # Default: IGNORE (None values excluded)
    default_dump = mr.dump(product)
    print(f"Default (IGNORE): 'description' in output = {'description' in default_dump}")
    # False - None values excluded

    # Runtime override: INCLUDE
    include_dump = mr.dump(product, none_value_handling=mr.NoneValueHandling.INCLUDE)
    print(f"INCLUDE: 'description' in output = {'description' in include_dump}")
    print(f"  description value: {include_dump.get('description')}")
    # True - None values included

    # Load with none_value_handling
    loaded_include = mr.load(Product, include_dump, none_value_handling=mr.NoneValueHandling.INCLUDE)
    assert loaded_include == product
    print("✓ none_value_handling works in both load and dump")

    # ============================================================
    # Parameter 3: decimal_places
    # ============================================================

    print("\n=== 3. decimal_places (runtime) ===")

    # Default: no rounding
    default_dump = mr.dump(product)
    print(f"Default (no rounding):")
    print(f"  unit_price: {default_dump['unit_price']}")
    print(f"  tax_rate: {default_dump['tax_rate']}")
    # unit_price: 999.10, tax_rate: 0.12 (default marshmallow precision)

    # Runtime override: 2 decimal places
    two_places_dump = mr.dump(product, decimal_places=2)
    print(f"decimal_places=2:")
    print(f"  unit_price: {two_places_dump['unit_price']}")
    print(f"  tax_rate: {two_places_dump['tax_rate']}")
    # unit_price: 1000.00, tax_rate: 0.12

    # Runtime override: 4 decimal places
    four_places_dump = mr.dump(product, decimal_places=4)
    print(f"decimal_places=4:")
    print(f"  unit_price: {four_places_dump['unit_price']}")
    print(f"  tax_rate: {four_places_dump['tax_rate']}")
    # unit_price: 999.9957, tax_rate: 0.1235

    print("✓ decimal_places controls precision at runtime")

    # ============================================================
    # Combining all three parameters
    # ============================================================

    print("\n=== 4. Combining all parameters ===")

    combined_dump = mr.dump(
        product,
        naming_case=mr.CAMEL_CASE,
        none_value_handling=mr.NoneValueHandling.INCLUDE,
        decimal_places=2,
    )

    print(f"Combined (camelCase + INCLUDE + 2 places):")
    print(f"  Keys: {list(combined_dump.keys())}")
    print(f"  unitPrice: {combined_dump['unitPrice']}")
    print(f"  description: {combined_dump['description']}")
    print("✓ All parameters work together!")

    # ============================================================
    # Runtime parameters override @mr.options
    # ============================================================

    print("\n=== 5. Runtime overrides @mr.options ===")

    configured_product = ConfiguredProduct(
        product_id=product.product_id,
        product_name=product.product_name,
        unit_price=product.unit_price,
        tax_rate=product.tax_rate,
        description=None,
    )

    # Default: uses @mr.options (camelCase, IGNORE, 2 places)
    default_configured = mr.dump(configured_product)
    print(f"With @mr.options (camelCase, IGNORE, 2 places):")
    print(f"  Keys: {list(default_configured.keys())}")
    print(f"  unitPrice: {default_configured['unitPrice']}")
    print(f"  description present: {'description' in default_configured}")

    # Runtime override: change all settings
    overridden = mr.dump(
        configured_product,
        naming_case=mr.CAPITAL_CAMEL_CASE,  # Override to PascalCase
        none_value_handling=mr.NoneValueHandling.INCLUDE,  # Override to INCLUDE
        decimal_places=4,  # Override to 4 places
    )

    print(f"\nRuntime override (PascalCase, INCLUDE, 4 places):")
    print(f"  Keys: {list(overridden.keys())}")
    print(f"  UnitPrice: {overridden['UnitPrice']}")
    print(f"  Description: {overridden['Description']}")
    print("✓ Runtime parameters override @mr.options!")

    # ============================================================
    # Schema generation with parameters
    # ============================================================

    print("\n=== 6. Schema generation with parameters ===")

    # Different schemas are cached per parameter combination
    schema1 = mr.schema(Product)
    schema2 = mr.schema(Product, naming_case=mr.CAMEL_CASE)
    schema3 = mr.schema(Product, decimal_places=2)
    schema4 = mr.schema(Product, naming_case=mr.CAMEL_CASE, decimal_places=2)

    print(f"Schemas are cached separately:")
    print(f"  Default schema: {id(schema1)}")
    print(f"  camelCase schema: {id(schema2)}")
    print(f"  decimal_places=2 schema: {id(schema3)}")
    print(f"  Combined schema: {id(schema4)}")
    print(f"  All different: {len({id(schema1), id(schema2), id(schema3), id(schema4)}) == 4}")
    print("✓ Schemas cached per parameter combination!")

    # ============================================================
    # Summary
    # ============================================================

    print("\n=== Summary ===")
    print("✓ naming_case: changes field names (snake_case ↔ camelCase ↔ PascalCase)")
    print("✓ none_value_handling: controls None serialization (IGNORE vs INCLUDE)")
    print("✓ decimal_places: controls decimal precision (2, 4, 9, etc.)")
    print("✓ All parameters work in: load(), dump(), load_many(), dump_many(), schema()")
    print("✓ Runtime parameters override @mr.options decorator")
    print("✓ Different parameter combinations create separate cached schemas")
