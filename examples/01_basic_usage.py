"""
Basic usage of marshmallow-recipe: simple types and serialization/deserialization.

This example demonstrates:
- All supported basic types
- Simple load/dump operations
- Optional types
- Default values
- Enums (StrEnum and IntEnum)
"""

import dataclasses
import datetime
import decimal
import enum
import uuid

import marshmallow_recipe as mr


# Define enums
class Status(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Priority(enum.IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    """Simple user model with all basic types."""

    # Required fields
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime.datetime
    is_active: bool
    balance: decimal.Decimal
    age: int
    rating: float
    birth_date: datetime.date
    status: Status
    priority: Priority

    # Optional fields
    last_login: datetime.datetime | None = None
    phone: str | None = None

    # Fields with defaults
    role: str = "user"
    notification_enabled: bool = True


if __name__ == "__main__":
    # Create a user instance
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
        last_login=datetime.datetime(2024, 3, 1, 14, 20, 0, tzinfo=datetime.UTC),
        phone="+1234567890",
    )

    print("=== Serialization (dump) ===")
    # Serialize to dict
    user_dict = mr.dump(user)
    print(f"Serialized user: {user_dict}")
    # Output: {'id': '550e8400-e29b-41d4-a716-446655440000', 'username': 'john_doe', ...}

    print("\n=== Deserialization (load) ===")
    # Deserialize from dict
    loaded_user = mr.load(User, user_dict)
    print(f"Loaded user: {loaded_user}")
    assert loaded_user == user
    print("✓ Serialization round-trip successful!")

    print("\n=== Working with many objects ===")
    # Serialize/deserialize lists
    users = [user, user]
    users_list = mr.dump_many(users)
    loaded_users = mr.load_many(User, users_list)
    assert loaded_users == users
    print(f"✓ Loaded {len(loaded_users)} users successfully")

    print("\n=== Optional fields with None ===")
    # Optional fields can be None
    user_without_optionals = User(
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
        # last_login and phone are None by default
    )

    dumped = mr.dump(user_without_optionals)
    print(f"User without optionals: {dumped}")
    # Note: None values are excluded from output by default
    assert "last_login" not in dumped
    assert "phone" not in dumped
    print("✓ None values excluded by default")

    print("\n=== Getting marshmallow schema ===")
    # You can get the generated marshmallow schema
    schema = mr.schema(User)
    print(f"Schema type: {type(schema)}")
    print("✓ Schema generated and cached automatically")
