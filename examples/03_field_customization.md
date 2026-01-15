# Field Customisation

Customising individual field behaviour with metadata.

## Custom Field Names

Map Python names to different JSON names:

```python
import dataclasses
import datetime
import uuid
from typing import Annotated

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ApiPayload:
    # Python snake_case → JSON camelCase
    user_id: Annotated[uuid.UUID, mr.meta(name="userId")]
    created_at: Annotated[datetime.datetime, mr.meta(name="createdAt")]
    is_active: Annotated[bool, mr.meta(name="isActive")]
    email: str  # No custom name


payload = ApiPayload(
    user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    created_at=datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC),
    is_active=True,
    email="john@example.com",
)

payload_dict = mr.dump(payload)
# {
#     'userId': '550e8400-e29b-41d4-a716-446655440000',
#     'createdAt': '2024-01-15T10:30:00+00:00',
#     'isActive': True,
#     'email': 'john@example.com'
# }
```

## String Transformations

```python
import re


def normalize_phone(phone: str) -> str:
    return re.sub(r"[^\d+]", "", phone)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CustomerProfile:
    # Strip whitespaces
    full_name: Annotated[str, mr.str_meta(strip_whitespaces=True)]

    # Custom name + strip
    email_address: Annotated[str, mr.str_meta(strip_whitespaces=True), mr.meta(name="email")]

    # Post-load transformation
    phone: Annotated[str, mr.str_meta(post_load=normalize_phone)]


profile = CustomerProfile(
    full_name="  John Doe  ",
    email_address="  john@example.com  ",
    phone="+1 (555) 123-4567",
)

profile_dict = mr.dump(profile)
# {
#     'full_name': 'John Doe',           # Stripped
#     'email': 'john@example.com',       # Stripped
#     'phone': '+15551234567'            # Normalized
# }
```

## Decimal Precision

Control decimal places per field with validation or rounding:

```python
import decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Transaction:
    id: uuid.UUID

    # 2 decimal places - validates (no rounding by default)
    amount: Annotated[decimal.Decimal, mr.decimal_meta(places=2)]

    # 4 decimal places - validates
    processing_fee: Annotated[decimal.Decimal, mr.decimal_meta(places=4)]

    # 9 decimal places - validates
    exchange_rate: Annotated[decimal.Decimal, mr.decimal_meta(places=9)]


transaction = Transaction(
    id=uuid.uuid4(),
    amount=decimal.Decimal("123.45"),
    processing_fee=decimal.Decimal("1.2345"),
    exchange_rate=decimal.Decimal("1.123456789"),
)

trans_dict = mr.dump(transaction)
# {
#     'amount': '123.45',            # Validated to have at most 2 places
#     'processing_fee': '1.2345',    # Validated to have at most 4 places
#     'exchange_rate': '1.123456789' # Validated to have at most 9 places
# }

# If value has too many decimal places, ValidationError is raised:
# Transaction(amount=decimal.Decimal("123.456"))  # ValidationError!
```

### Rounding Mode

To enable rounding instead of validation, specify a `rounding` mode:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class RoundedTransaction:
    # Rounding enabled with ROUND_HALF_UP
    amount: Annotated[decimal.Decimal, mr.decimal_meta(places=2, rounding=decimal.ROUND_HALF_UP)]

    # Rounding with ROUND_DOWN
    fee: Annotated[decimal.Decimal, mr.decimal_meta(places=2, rounding=decimal.ROUND_DOWN)]


trans = RoundedTransaction(
    amount=decimal.Decimal("123.456"),
    fee=decimal.Decimal("1.999"),
)

trans_dict = mr.dump(trans)
# {
#     'amount': '123.46',  # Rounded up
#     'fee': '1.99',       # Rounded down
# }
```

## Custom Datetime Formats

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    id: int
    name: str

    # Custom format: YYYY-MM-DD HH:MM:SS
    scheduled_at: Annotated[
        datetime.datetime,
        mr.datetime_meta(format="%Y-%m-%d %H:%M:%S"),
    ]


event = Event(
    id=1,
    name="Conference",
    scheduled_at=datetime.datetime(2024, 12, 25, 14, 30, 0),
)

event_dict = mr.dump(event)
# {
#     'id': 1,
#     'name': 'Conference',
#     'scheduled_at': '2024-12-25 14:30:00'  # Custom format
# }
```

## Field Descriptions

Add documentation to your fields using descriptions:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    # Add description via metadata
    username: Annotated[str, mr.str_meta(description="Unique username for the user")]

    email: Annotated[
        str,
        mr.str_meta(strip_whitespaces=True, description="Primary email address for notifications"),
    ]

    age: Annotated[int, mr.meta(description="User's age in years")]


# Access descriptions from the generated schema
user_schema = mr.schema(User)
username_field = user_schema.fields["username"]
print(username_field.metadata["description"])
# Output: "Unique username for the user"
```

The description is stored in the field's `metadata` dictionary and can be used for:

- Generating API documentation
- Creating interactive forms
- OpenAPI/Swagger schema generation
```
