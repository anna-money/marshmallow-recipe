# Validation

Field validation patterns in marshmallow-recipe.

## Lambda Validators

Custom validation logic with lambda functions:

```python
import dataclasses
from typing import Annotated

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistration:
    # Password: at least 8 characters
    password: Annotated[str, mr.meta(validate=lambda x: len(x) >= 8)]

    # Age: between 18 and 120
    age: Annotated[
        int,
        mr.meta(validate=mr.validate(lambda x: 18 <= x <= 120, error="Age must be between 18 and 120")),
    ]

    # Expiry month: 1-12
    expiry_month: Annotated[int, mr.meta(validate=lambda x: 1 <= x <= 12)]


user = UserRegistration(
    password="secure_password_123",
    age=25,
    expiry_month=12,
)

user_dict = mr.dump(user)
loaded_user = mr.load(UserRegistration, user_dict)
```

## Regex Validation

Pattern matching with `mr.regexp_validate()`:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ContactInfo:
    # Username: alphanumeric, 3-20 characters
    username: Annotated[
        str,
        mr.str_meta(
            validate=mr.regexp_validate(
                r"^[a-zA-Z0-9]{3,20}$",
                error="Username must be 3-20 alphanumeric characters"
            )
        ),
    ]

    # Phone: international format
    phone: Annotated[
        str,
        mr.str_meta(validate=mr.regexp_validate(r"^\+?[1-9]\d{1,14}$", error="Invalid phone number")),
    ]


contact = ContactInfo(
    username="john_doe",
    phone="+15551234567",
)
```

## Email Validation

Email address validation with `mr.email_validate()`:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserAccount:
    # Primary email: standard validation
    email: Annotated[str, mr.str_meta(validate=mr.email_validate())]

    # Backup email: custom error message
    backup_email: Annotated[
        str,
        mr.str_meta(
            validate=mr.email_validate(error="Please provide a valid backup email address")
        ),
    ]


user = UserAccount(
    email="user@example.com",
    backup_email="backup@domain.org",
)

# Valid email formats:
# - user@example.com
# - test.user+tag@domain.co.uk
# - user@localhost
# - "quoted.user"@example.com
# - user@münchen.de (internationalized domains)

# Invalid formats raise ValidationError:
# - Empty string
# - Missing @ sign
# - Invalid domain
# - Invalid user part
```

## Decimal Range Validation

Range validation for decimal fields using `mr.decimal_meta()`:

```python
import decimal

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    # Price: must be greater than 0 (int bounds auto-converted to Decimal)
    price: Annotated[
        decimal.Decimal,
        mr.decimal_meta(gt=0),
    ]

    # Discount: must be between 0 and 100 (inclusive)
    discount: Annotated[
        decimal.Decimal,
        mr.decimal_meta(gte=0, lte=100),
    ]

    # Tax rate: must be less than 1 (Decimal bounds also supported)
    tax_rate: Annotated[
        decimal.Decimal,
        mr.decimal_meta(lt=decimal.Decimal("1"), places=4),
    ]


product = Product(
    price=decimal.Decimal("9.99"),
    discount=decimal.Decimal("15.00"),
    tax_rate=decimal.Decimal("0.2100"),
)

product_dict = mr.dump(product)
loaded_product = mr.load(Product, product_dict)
```

Range operators: `gt` (>), `gte` (>=), `lt` (<), `lte` (<=).

Custom error messages for range validation:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Invoice:
    amount: Annotated[
        decimal.Decimal,
        mr.decimal_meta(
            gt=decimal.Decimal("0"),
            gt_error="Amount must be positive",
            lte=decimal.Decimal("1000000"),
            lte_error="Amount cannot exceed 1,000,000",
        ),
    ]
```

## Custom Error Messages

Using `mr.validate()` helper for readable error messages:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PaymentInfo:
    # Card number: exactly 16 digits
    card_number: Annotated[
        str,
        mr.str_meta(validate=mr.regexp_validate(r"^\d{16}$", error="Card number must be exactly 16 digits")),
    ]

    # CVV: 3 or 4 digits
    cvv: Annotated[
        str,
        mr.str_meta(validate=mr.regexp_validate(r"^\d{3,4}$", error="CVV must be 3 or 4 digits")),
    ]

    # Amount: must be positive
    amount: Annotated[
        float,
        mr.meta(validate=mr.validate(lambda x: x > 0, error="Amount must be positive")),
    ]
```

## Field-Level Error Messages

Customize marshmallow's built-in error messages using explicit error parameters:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserProfile:
    # Custom "required" error message
    username: Annotated[
        str,
        mr.str_meta(required_error="Please provide a username"),
    ]

    # Custom "required" and "none" error messages
    email: Annotated[
        str,
        mr.str_meta(
            required_error="Email address is required",
            none_error="Email cannot be empty",
        ),
    ]

    # Custom "invalid" error message
    age: Annotated[
        int,
        mr.meta(invalid_error="Age must be a valid number"),
    ]


# Missing required field
try:
    mr.load(UserProfile, {"email": "user@example.com", "age": 25})
except m.ValidationError as e:
    # e.messages == {'username': ['Please provide a username']}
    pass

# None value for non-nullable field
try:
    mr.load(UserProfile, {"username": "john", "email": None, "age": 25})
except m.ValidationError as e:
    # e.messages == {'email': ['Email cannot be empty']}
    pass

# Invalid type
try:
    mr.load(UserProfile, {"username": "john", "email": "john@example.com", "age": "abc"})
except m.ValidationError as e:
    # e.messages == {'age': ['Age must be a valid number']}
    pass
```

Available error message parameters:
- `required_error`: Error when field is missing from input
- `none_error`: Error when field has None value but doesn't allow None
- `invalid_error`: Error for invalid type or format

## Collection Item Validation

Validate individual items in collections:

```python
import re


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ProductInventory:
    # SKUs: each must be non-empty
    skus: Annotated[
        list[str],
        mr.list_meta(validate_item=lambda x: len(x) > 0),
    ] = dataclasses.field(default_factory=list)

    # Barcodes: each must be exactly 13 digits (EAN-13)
    barcodes: Annotated[
        list[str],
        mr.list_meta(validate_item=lambda x: re.match(r"^\d{13}$", x) is not None),
    ] = dataclasses.field(default_factory=list)

    # Categories: each must be non-empty
    categories: Annotated[
        set[str],
        mr.set_meta(validate_item=lambda x: len(x) > 0),
    ] = dataclasses.field(default_factory=set)

    # Tags: each must be 2-20 characters
    tags: Annotated[
        tuple[str, ...],
        mr.tuple_meta(validate_item=lambda x: 2 <= len(x) <= 20),
    ] = dataclasses.field(default_factory=tuple)


inventory = ProductInventory(
    skus=["SKU001", "SKU002", "SKU003"],
    barcodes=["1234567890123", "9876543210987"],
    categories={"electronics", "accessories", "portable"},
    tags=("new", "featured", "popular"),
)

inventory_dict = mr.dump(inventory)
loaded_inventory = mr.load(ProductInventory, inventory_dict)
```

## Combining Validation with Transformations

Whitespace is stripped before validation:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CleanedUser:
    # Email: strip whitespace AND validate format
    email: Annotated[
        str,
        mr.str_meta(
            strip_whitespaces=True,
            validate=mr.email_validate(),
        ),
    ]

    # Username: strip AND validate length
    username: Annotated[
        str,
        mr.str_meta(strip_whitespaces=True, validate=lambda x: 3 <= len(x) <= 20),
    ]


cleaned_user = mr.load(
    CleanedUser,
    {
        "email": "  john@example.com  ",  # Stripped before validation
        "username": "  john_doe  ",  # Stripped before validation
    },
)

# Results after stripping and validation
# cleaned_user.email == "john@example.com"
# cleaned_user.username == "john_doe"
```

## Validation Errors

Validation failures raise `marshmallow.ValidationError`:

```python
import marshmallow as m

# Invalid data
try:
    mr.load(
        UserRegistration,
        {
            "password": "short",  # Too short (< 8 chars)
            "age": 25,
            "expiry_month": 12,
        },
    )
except m.ValidationError as e:
    # e.messages contains field-level errors
    # {'password': ['Invalid value.']}
    pass
```

See [12_validation_errors.md](12_validation_errors.md) for detailed error handling patterns.
