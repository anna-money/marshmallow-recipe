# Basic Usage

Basic types and serialisation/deserialisation with marshmallow-recipe.

## Supported Types

All standard Python types work out of the box:

```python
import dataclasses
import datetime
import decimal
import enum
import uuid

import marshmallow_recipe as mr


class Status(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Priority(enum.IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    # Basic types
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime.datetime
    is_active: bool
    balance: decimal.Decimal
    age: int
    rating: float
    birth_date: datetime.date

    # Enums
    status: Status
    priority: Priority

    # Optional fields
    last_login: datetime.datetime | None = None
    phone: str | None = None

    # Fields with defaults
    role: str = "user"
    notification_enabled: bool = True
```

## Serialisation (dump)

```python
user = User(
    id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    username="john_doe",
    email="john@example.com",
    created_at=datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC),
    is_active=True,
    balance=decimal.Decimal("1234.56"),
    age=30,
    rating=4.5,
    birth_date=datetime.date(1994, 5, 20),
    status=Status.ACTIVE,
    priority=Priority.HIGH,
)

user_dict = mr.dump(user)
# Result:
# {
#     'id': '550e8400-e29b-41d4-a716-446655440000',
#     'username': 'john_doe',
#     'email': 'john@example.com',
#     'created_at': '2024-01-15T10:30:00+00:00',
#     'is_active': True,
#     'balance': '1234.56',
#     'age': 30,
#     'rating': 4.5,
#     'birth_date': '1994-05-20',
#     'status': 'active',
#     'priority': 3,
#     'role': 'user',
#     'notification_enabled': True
# }
```

## Deserialisation (load)

```python
loaded_user = mr.load(User, user_dict)
assert loaded_user == user  # Round-trip successful!
```

## Working with Many Objects

```python
users = [user, user]
users_list = mr.dump_many(users)
loaded_users = mr.load_many(User, users_list)
assert loaded_users == users
```

## Optional Fields

None values are excluded from output by default:

```python
user_minimal = User(
    id=uuid.uuid4(),
    username="jane_doe",
    email="jane@example.com",
    created_at=datetime.datetime.now(datetime.UTC),
    is_active=True,
    balance=decimal.Decimal("0.00"),
    age=25,
    rating=5.0,
    birth_date=datetime.date(1999, 1, 1),
    status=Status.INACTIVE,
    priority=Priority.LOW,
    # last_login and phone are None
)

dumped = mr.dump(user_minimal)
# 'last_login' and 'phone' NOT in dumped dict
assert "last_login" not in dumped
assert "phone" not in dumped
```

## Schema Generation

Schemas are generated and cached automatically:

```python
schema = mr.schema(User)
# Returns: marshmallow.Schema instance
# Cached per dataclass + parameters combination
```

## NewType Support

NewType works transparently (treated as underlying type):

```python
from typing import NewType

UserId = NewType("UserId", int)
Email = NewType("Email", str)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Account:
    user_id: UserId
    email: Email
    balance: decimal.Decimal


account = Account(
    user_id=UserId(12345),
    email=Email("user@example.com"),
    balance=decimal.Decimal("100.50"),
)

account_dict = mr.dump(account)
# NewType is transparent at runtime:
# {'user_id': 12345, 'email': 'user@example.com', 'balance': '100.50'}
```
