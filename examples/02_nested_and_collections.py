"""
Nested dataclasses and collections in marshmallow-recipe.

This example demonstrates:
- Nested dataclasses
- Lists, sets, frozensets, tuples
- Dictionaries with complex keys/values
- Optional nested structures
- Collections of nested dataclasses
"""

import dataclasses
import datetime
import decimal
import uuid
from typing import Any

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    """Nested address dataclass."""

    street: str
    city: str
    country: str
    postal_code: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PhoneNumber:
    """Nested phone number dataclass."""

    country_code: str
    number: str
    type: str  # e.g., "mobile", "home"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    """Product with nested pricing."""

    id: uuid.UUID
    name: str
    price: decimal.Decimal
    tags: set[str]  # Set of tags
    categories: frozenset[str]  # Immutable set of categories
    features: tuple[str, ...]  # Tuple of features


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    """Order with nested products."""

    id: uuid.UUID
    customer_id: uuid.UUID
    products: list[Product]  # List of nested dataclasses
    quantities: dict[uuid.UUID, int]  # Dict mapping product ID to quantity
    total: decimal.Decimal
    created_at: datetime.datetime


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Customer:
    """Customer with complex nested structures."""

    id: uuid.UUID
    name: str
    email: str

    # Nested dataclass
    primary_address: Address

    # Optional nested dataclass
    billing_address: Address | None = None

    # List of nested dataclasses
    phone_numbers: list[PhoneNumber] = dataclasses.field(default_factory=list)

    # Dict with date keys and decimal values
    balance_history: dict[datetime.date, decimal.Decimal] = dataclasses.field(default_factory=dict)

    # Dict with complex nested values
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)


if __name__ == "__main__":
    print("=== Nested dataclasses ===")

    # Create nested structures
    address = Address(
        street="123 Main St",
        city="New York",
        country="USA",
        postal_code="10001",
    )

    phones = [
        PhoneNumber(country_code="+1", number="5551234", type="mobile"),
        PhoneNumber(country_code="+1", number="5555678", type="home"),
    ]

    customer = Customer(
        id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        name="John Doe",
        email="john@example.com",
        primary_address=address,
        billing_address=address,  # Same as primary
        phone_numbers=phones,
        balance_history={
            datetime.date(2024, 1, 1): decimal.Decimal("100.00"),
            datetime.date(2024, 2, 1): decimal.Decimal("150.50"),
        },
        metadata={"vip": True, "notes": "Good customer"},
    )

    # Serialize nested structure
    customer_dict = mr.dump(customer)
    print(f"Serialized customer with nested structures:")
    print(f"  - Name: {customer_dict['name']}")
    print(f"  - Address: {customer_dict['primary_address']}")
    print(f"  - Phones: {customer_dict['phone_numbers']}")
    print(f"  - Balance history: {customer_dict['balance_history']}")

    # Deserialize back
    loaded_customer = mr.load(Customer, customer_dict)
    assert loaded_customer == customer
    print("✓ Nested structures round-trip successful!")

    print("\n=== Collections of nested dataclasses ===")

    # Create products with various collection types
    products = [
        Product(
            id=uuid.uuid4(),
            name="Laptop",
            price=decimal.Decimal("999.99"),
            tags={"electronics", "computers", "portable"},
            categories=frozenset(["electronics", "office"]),
            features=("16GB RAM", "512GB SSD", "14-inch display"),
        ),
        Product(
            id=uuid.uuid4(),
            name="Mouse",
            price=decimal.Decimal("29.99"),
            tags={"electronics", "accessories"},
            categories=frozenset(["electronics", "peripherals"]),
            features=("wireless", "ergonomic"),
        ),
    ]

    order = Order(
        id=uuid.uuid4(),
        customer_id=customer.id,
        products=products,
        quantities={products[0].id: 1, products[1].id: 2},
        total=decimal.Decimal("1059.97"),
        created_at=datetime.datetime.now(datetime.UTC),
    )

    order_dict = mr.dump(order)
    print(f"Order with {len(order_dict['products'])} products")
    print(f"  - Product 1 tags: {order_dict['products'][0]['tags']}")
    print(f"  - Product 1 features: {order_dict['products'][0]['features']}")

    loaded_order = mr.load(Order, order_dict)
    assert loaded_order == order
    print("✓ Collections round-trip successful!")

    print("\n=== Dict with complex keys ===")

    # Note: Date keys in dict are serialized as ISO strings
    balance_history_raw = customer_dict["balance_history"]
    print(f"Balance history (serialized): {balance_history_raw}")
    # Keys are automatically converted: datetime.date → str on dump, str → datetime.date on load
    print("✓ Complex dict keys handled automatically!")

    print("\n=== Optional nested structures ===")

    # Customer without billing address
    customer_minimal = Customer(
        id=uuid.uuid4(),
        name="Jane Doe",
        email="jane@example.com",
        primary_address=address,
        # billing_address is None (optional)
        # Other collections use default_factory
    )

    dumped_minimal = mr.dump(customer_minimal)
    print(f"Minimal customer (no billing address):")
    print(f"  - billing_address in dict: {'billing_address' in dumped_minimal}")
    print(f"  - phone_numbers: {dumped_minimal.get('phone_numbers', [])}")

    loaded_minimal = mr.load(Customer, dumped_minimal)
    assert loaded_minimal.billing_address is None
    assert loaded_minimal.phone_numbers == []
    print("✓ Optional nested structures work correctly!")
