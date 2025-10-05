# Nested Dataclasses and Collections

Working with nested structures and various collection types.

## Nested Dataclasses

```python
import dataclasses
import datetime
import decimal
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    street: str
    city: str
    country: str
    postal_code: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PhoneNumber:
    country_code: str
    number: str
    type: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Customer:
    id: uuid.UUID
    name: str
    email: str

    # Required nested dataclass
    primary_address: Address

    # Optional nested dataclass
    billing_address: Address | None = None

    # List of nested dataclasses
    phone_numbers: list[PhoneNumber] = dataclasses.field(default_factory=list)

    # Dict with date keys and decimal values
    balance_history: dict[datetime.date, decimal.Decimal] = dataclasses.field(default_factory=dict)


# Create nested structure
customer = Customer(
    id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    name="John Doe",
    email="john@example.com",
    primary_address=Address(
        street="123 Main St",
        city="New York",
        country="USA",
        postal_code="10001",
    ),
    phone_numbers=[
        PhoneNumber(country_code="+1", number="5551234", type="mobile"),
        PhoneNumber(country_code="+1", number="5555678", type="home"),
    ],
    balance_history={
        datetime.date(2024, 1, 1): decimal.Decimal("100.00"),
        datetime.date(2024, 2, 1): decimal.Decimal("150.50"),
    },
)

# Serialise and deserialise
customer_dict = mr.dump(customer)
loaded_customer = mr.load(Customer, customer_dict)
assert loaded_customer == customer
```

## Collection Types

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    id: uuid.UUID
    name: str
    price: decimal.Decimal

    # Set of tags
    tags: set[str]

    # Immutable set of categories
    categories: frozenset[str]

    # Tuple of features
    features: tuple[str, ...]


product = Product(
    id=uuid.uuid4(),
    name="Laptop",
    price=decimal.Decimal("999.99"),
    tags={"electronics", "computers", "portable"},
    categories=frozenset(["electronics", "office"]),
    features=("16GB RAM", "512GB SSD", "14-inch display"),
)

product_dict = mr.dump(product)
loaded_product = mr.load(Product, product_dict)
```

## Dictionary with Complex Keys

Date keys are automatically converted:

```python
# Serialisation: datetime.date → str
# {
#     "2024-01-01": "100.00",
#     "2024-02-01": "150.50"
# }

# Deserialisation: str → datetime.date
# Automatic conversion both ways
```

## collections.abc Types

Abstract collection types work transparently:

```python
from collections.abc import Mapping, Sequence, Set


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Inventory:
    # Sequence instead of list - accepts list, tuple, etc.
    items: Sequence[str]

    # Set instead of set - abstract set type
    unique_ids: Set[int]

    # Mapping instead of dict - abstract mapping type
    metadata: Mapping[str, str]


inventory = Inventory(
    items=["item1", "item2", "item3"],
    unique_ids={1, 2, 3},
    metadata={"key": "value"},
)

inventory_dict = mr.dump(inventory)
loaded_inventory = mr.load(Inventory, inventory_dict)

# After load: Sequence → list, Set → set, Mapping → dict
assert isinstance(loaded_inventory.items, list)
assert isinstance(loaded_inventory.unique_ids, set)
assert isinstance(loaded_inventory.metadata, dict)
```

## Optional Nested Structures

```python
customer_minimal = Customer(
    id=uuid.uuid4(),
    name="Jane Doe",
    email="jane@example.com",
    primary_address=Address(
        street="456 Oak Ave",
        city="Boston",
        country="USA",
        postal_code="02101",
    ),
    # billing_address is None
    # phone_numbers uses default_factory (empty list)
    # balance_history uses default_factory (empty dict)
)

dumped = mr.dump(customer_minimal)
# billing_address not in dict (None excluded by default)
assert "billing_address" not in dumped
assert dumped["phone_numbers"] == []
assert dumped["balance_history"] == {}
```
