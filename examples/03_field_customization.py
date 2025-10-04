"""
Field customization in marshmallow-recipe.

This example demonstrates:
- Custom field names with mr.meta(name="...")
- String transformations (strip_whitespaces, post_load)
- Decimal precision control
- Field validation with custom validators
- Regex validation
- Collection item validation
- Using Annotated type hints
"""

import dataclasses
import decimal
import re
import uuid
from typing import Annotated

import marshmallow as m

import marshmallow_recipe as mr


def normalize_phone(phone: str) -> str:
    """Remove all non-digit characters from phone number."""
    return re.sub(r"[^\d+]", "", phone)


def normalize_address(address: str) -> str:
    """Normalize address: strip and replace multiple spaces with single space."""
    return " ".join(address.split())


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PaymentCard:
    """Payment card with field customization."""

    # Custom field name (snake_case in Python, camelCase in JSON)
    card_id: Annotated[uuid.UUID, mr.meta(name="cardId")]

    # Strip whitespaces from card holder name
    card_holder: Annotated[str, mr.str_meta(strip_whitespaces=True)]

    # PAN with regex validation
    card_number: Annotated[
        str,
        mr.str_meta(
            validate=mr.regexp_validate(r"^\d{16}$", error="Card number must be exactly 16 digits")
        ),
    ]

    # CVV with regex validation
    cvv: Annotated[
        str, mr.str_meta(validate=mr.regexp_validate(r"^\d{3,4}$", error="CVV must be 3 or 4 digits"))
    ]

    # Expiry month with range validation
    expiry_month: Annotated[int, mr.meta(validate=lambda x: 1 <= x <= 12)]

    # Expiry year with custom validation
    expiry_year: Annotated[int, mr.meta(validate=lambda x: x >= 2024)]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Transaction:
    """Financial transaction with decimal precision."""

    id: uuid.UUID

    # Amount with 2 decimal places (standard for most currencies)
    amount: Annotated[decimal.Decimal, mr.decimal_meta(places=2)]

    # Fee with 4 decimal places (higher precision for fees)
    processing_fee: Annotated[decimal.Decimal, mr.decimal_meta(places=4)]

    # Exchange rate with 9 decimal places (very high precision)
    exchange_rate: Annotated[decimal.Decimal, mr.decimal_meta(places=9)]

    # Amount with validation
    credit_limit: Annotated[
        decimal.Decimal,
        mr.decimal_meta(places=2, validate=lambda x: x > 0),
    ]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CustomerProfile:
    """Customer profile with string transformations."""

    # Email with custom field name
    email_address: Annotated[str, mr.meta(name="email")]

    # Phone with post_load transformation
    phone: Annotated[str, mr.str_meta(post_load=normalize_phone)]

    # Address with both strip and normalization
    shipping_address: Annotated[str, mr.str_meta(strip_whitespaces=True, post_load=normalize_address)]

    # Optional postal code with strip
    postal_code: Annotated[str | None, mr.str_meta(strip_whitespaces=True)] = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ProductCatalog:
    """Product catalog with collection validation."""

    # List of SKUs, each must be non-empty
    skus: Annotated[
        list[str], mr.list_meta(validate_item=lambda x: len(x) > 0)
    ] = dataclasses.field(default_factory=list)

    # Set of categories, each must be non-empty
    categories: Annotated[
        set[str], mr.set_meta(validate_item=lambda x: len(x) > 0)
    ] = dataclasses.field(default_factory=set)

    # Tuple of barcodes, each must match pattern
    barcodes: Annotated[
        tuple[str, ...], mr.tuple_meta(validate_item=lambda x: re.match(r"^\d{13}$", x) is not None)
    ] = dataclasses.field(default_factory=tuple)


if __name__ == "__main__":
    print("=== Custom field names ===")

    card = PaymentCard(
        card_id=uuid.uuid4(),
        card_holder="  John Doe  ",  # Will be stripped
        card_number="1234567812345678",
        cvv="123",
        expiry_month=12,
        expiry_year=2025,
    )

    card_dict = mr.dump(card)
    print(f"Serialized card:")
    print(f"  - Field 'card_id' → 'cardId': {card_dict.get('cardId')}")
    print(f"  - Card holder (stripped): '{card_dict['card_holder']}'")

    loaded_card = mr.load(PaymentCard, card_dict)
    assert loaded_card.card_holder == "John Doe"  # Whitespace stripped
    print("✓ Custom field names and whitespace stripping work!")

    print("\n=== Validation ===")

    # Try invalid card number
    try:
        mr.load(
            PaymentCard,
            {
                "cardId": str(uuid.uuid4()),
                "card_holder": "John Doe",
                "card_number": "123",  # Invalid: too short
                "cvv": "123",
                "expiry_month": 12,
                "expiry_year": 2025,
            },
        )
        print("ERROR: Should have raised validation error!")
    except m.ValidationError as e:
        errors = e.messages
        if isinstance(errors, dict):
            print(f"✓ Validation caught invalid card number: {errors.get('card_number')}")

    # Try invalid expiry month
    try:
        mr.load(
            PaymentCard,
            {
                "cardId": str(uuid.uuid4()),
                "card_holder": "John Doe",
                "card_number": "1234567812345678",
                "cvv": "123",
                "expiry_month": 13,  # Invalid: > 12
                "expiry_year": 2025,
            },
        )
        print("ERROR: Should have raised validation error!")
    except m.ValidationError as e:
        print(f"✓ Validation caught invalid expiry month")

    print("\n=== Decimal precision ===")

    transaction = Transaction(
        id=uuid.uuid4(),
        amount=decimal.Decimal("123.456789"),  # Will be rounded to 2 places
        processing_fee=decimal.Decimal("1.23456789"),  # Will be rounded to 4 places
        exchange_rate=decimal.Decimal("1.123456789123"),  # Will be rounded to 9 places
        credit_limit=decimal.Decimal("10000.00"),
    )

    trans_dict = mr.dump(transaction)
    print(f"Transaction with different decimal precisions:")
    print(f"  - Amount (2 places): {trans_dict['amount']}")
    print(f"  - Processing fee (4 places): {trans_dict['processing_fee']}")
    print(f"  - Exchange rate (9 places): {trans_dict['exchange_rate']}")

    assert trans_dict["amount"] == "123.46"
    assert trans_dict["processing_fee"] == "1.2346"
    assert trans_dict["exchange_rate"] == "1.123456789"
    print("✓ Decimal precision control works!")

    print("\n=== String transformations ===")

    profile = CustomerProfile(
        email_address="john@example.com",
        phone="+1 (555) 123-4567",  # Will be normalized to +15551234567
        shipping_address="  123   Main   St  ",  # Multiple spaces will be normalized
        postal_code="  10001  ",  # Will be stripped
    )

    profile_dict = mr.dump(profile)
    print(f"Profile with transformations:")
    print(f"  - Field 'email_address' → 'email': {profile_dict.get('email')}")
    print(f"  - Phone normalized: {profile_dict['phone']}")
    print(f"  - Address normalized: '{profile_dict['shipping_address']}'")
    print(f"  - Postal code stripped: '{profile_dict.get('postal_code', 'N/A')}'")

    loaded_profile = mr.load(CustomerProfile, profile_dict)
    assert loaded_profile.phone == "+15551234567"
    assert loaded_profile.shipping_address == "123 Main St"
    assert loaded_profile.postal_code == "10001"
    print("✓ String transformations work!")

    print("\n=== Collection item validation ===")

    # Valid catalog
    catalog = ProductCatalog(
        skus=["SKU001", "SKU002"],
        categories={"electronics", "accessories"},
        barcodes=("1234567890123", "9876543210987"),
    )

    catalog_dict = mr.dump(catalog)
    loaded_catalog = mr.load(ProductCatalog, catalog_dict)
    assert loaded_catalog == catalog
    print("✓ Valid collection items passed validation")

    # Try invalid SKU (empty string)
    try:
        mr.load(ProductCatalog, {"skus": ["SKU001", ""]})  # Empty string
        print("ERROR: Should have raised validation error!")
    except m.ValidationError:
        print("✓ Collection item validation caught empty SKU")

    # Try invalid barcode (wrong format)
    try:
        mr.load(ProductCatalog, {"barcodes": ["12345"]})  # Too short
        print("ERROR: Should have raised validation error!")
    except m.ValidationError:
        print("✓ Collection item validation caught invalid barcode format")
