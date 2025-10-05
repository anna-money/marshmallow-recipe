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

Control decimal places per field:

```python
import decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Transaction:
    id: uuid.UUID

    # 2 decimal places (standard currencies)
    amount: Annotated[decimal.Decimal, mr.decimal_meta(places=2)]

    # 4 decimal places (fees)
    processing_fee: Annotated[decimal.Decimal, mr.decimal_meta(places=4)]

    # 9 decimal places (forex/crypto)
    exchange_rate: Annotated[decimal.Decimal, mr.decimal_meta(places=9)]


transaction = Transaction(
    id=uuid.uuid4(),
    amount=decimal.Decimal("123.456789"),
    processing_fee=decimal.Decimal("1.23456789"),
    exchange_rate=decimal.Decimal("1.123456789123"),
)

trans_dict = mr.dump(transaction)
# {
#     'amount': '123.46',            # Rounded to 2 places
#     'processing_fee': '1.2346',    # Rounded to 4 places
#     'exchange_rate': '1.123456789' # Rounded to 9 places
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

    # Custom format: DD/MM/YYYY
    event_date: Annotated[
        datetime.date,
        mr.datetime_meta(format="%d/%m/%Y"),
    ]


event = Event(
    id=1,
    name="Conference",
    scheduled_at=datetime.datetime(2024, 12, 25, 14, 30, 0),
    event_date=datetime.date(2024, 12, 25),
)

event_dict = mr.dump(event)
# {
#     'id': 1,
#     'name': 'Conference',
#     'scheduled_at': '2024-12-25 14:30:00',  # Custom format
#     'event_date': '25/12/2024'               # Custom format
# }
```

## Combining Customisations

Multiple customisations can be combined:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ComplexModel:
    # Custom name + strip
    user_name: Annotated[str, mr.str_meta(strip_whitespaces=True), mr.meta(name="userName")]

    # Custom name + decimal precision
    total_amount: Annotated[decimal.Decimal, mr.decimal_meta(places=2), mr.meta(name="totalAmount")]

    # Custom name + datetime format
    last_updated: Annotated[
        datetime.datetime,
        mr.datetime_meta(format="%Y-%m-%d %H:%M"),
        mr.meta(name="lastUpdated"),
    ]


complex = ComplexModel(
    user_name="  Alice  ",
    total_amount=decimal.Decimal("99.999"),
    last_updated=datetime.datetime(2024, 3, 15, 10, 30, 45),
)

complex_dict = mr.dump(complex)
# {
#     'userName': 'Alice',           # Stripped
#     'totalAmount': '100.00',       # 2 places
#     'lastUpdated': '2024-03-15 10:30'  # Custom format
# }
```
