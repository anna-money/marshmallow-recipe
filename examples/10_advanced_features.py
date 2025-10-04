"""
Advanced features and edge cases in marshmallow-recipe.

This example demonstrates:
- Cyclic/self-referencing structures
- @mr.pre_load hooks for data transformation
- add_pre_load() for programmatically adding hooks
- get_validation_field_errors() for structured error handling
- datetime_meta(format=...) for custom datetime formats
- validate() helper function
- collections.abc types (Sequence, Set, Mapping)
- NewType support
"""

import dataclasses
import datetime
from collections.abc import Mapping, Sequence, Set
from typing import Annotated, Any, NewType

import marshmallow as m

import marshmallow_recipe as mr


# ============================================================
# Cyclic/self-referencing structures
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TreeNode:
    """Tree node with optional parent reference (cyclic)."""

    id: int
    name: str
    parent: "TreeNode | None" = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Comment:
    """Comment with replies (self-referencing list)."""

    id: int
    text: str
    author: str
    replies: list["Comment"] = dataclasses.field(default_factory=list)


# ============================================================
# @mr.pre_load hooks
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NormalizedUser:
    """User with email normalization via @mr.pre_load decorator."""

    id: int
    email: str
    username: str

    @staticmethod
    @mr.pre_load
    def normalize_email(data: dict[str, Any]) -> dict[str, Any]:
        """Normalize email to lowercase before loading."""
        if "email" in data:
            data = {**data, "email": data["email"].lower().strip()}
        return data


# NewType examples
UserId = NewType("UserId", int)
Email = NewType("Email", str)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Event with custom datetime format."""

    id: int
    name: str
    # Custom datetime format: YYYY-MM-DD HH:MM:SS
    scheduled_at: Annotated[
        datetime.datetime, mr.datetime_meta(format="%Y-%m-%d %H:%M:%S")
    ]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ValidationExample:
    """Model with complex validation for error handling demo."""

    user_id: Annotated[int, mr.meta(validate=lambda x: x > 0)]
    email: Annotated[
        str, mr.str_meta(validate=mr.regexp_validate(r"^[\w\.-]+@[\w\.-]+\.\w+$"))
    ]
    age: Annotated[int, mr.meta(validate=mr.validate(lambda x: 18 <= x <= 120, error="Age must be between 18 and 120"))]
    tags: Annotated[list[str], mr.list_meta(validate_item=lambda x: len(x) > 0)]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CollectionTypes:
    """Using collections.abc types instead of built-in types."""

    # Sequence instead of list - accepts list, tuple, etc.
    items: Sequence[str]

    # Set instead of set - abstract set type
    unique_items: Set[int]

    # Mapping instead of dict - abstract mapping type
    metadata: Mapping[str, str]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserWithNewType:
    """Using NewType for type safety."""

    user_id: UserId  # NewType wrapping int
    email: Email  # NewType wrapping str
    name: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DataWithPreLoad:
    """Model for demonstrating add_pre_load."""

    value: str


# Add pre_load hook programmatically (not using decorator)
mr.add_pre_load(DataWithPreLoad, lambda data: {**data, "value": data["value"].upper()})


if __name__ == "__main__":
    print("=== 1. Cyclic/self-referencing structures ===")

    # Tree with parent reference
    root = TreeNode(id=1, name="root", parent=None)
    child = TreeNode(id=2, name="child", parent=root)

    child_dumped = mr.dump(child)
    print(f"Child node with parent: {child_dumped}")
    assert child_dumped["parent"]["name"] == "root"

    child_loaded = mr.load(TreeNode, child_dumped)
    assert child_loaded.parent is not None
    assert child_loaded.parent.name == "root"
    print("✓ Cyclic references (parent-child) work!")

    # Comment with nested replies
    comment = Comment(
        id=1,
        text="Main comment",
        author="Alice",
        replies=[
            Comment(id=2, text="Reply 1", author="Bob", replies=[]),
            Comment(
                id=3,
                text="Reply 2",
                author="Charlie",
                replies=[Comment(id=4, text="Nested reply", author="Dave", replies=[])],
            ),
        ],
    )

    comment_dumped = mr.dump(comment)
    print(f"Comment with {len(comment_dumped['replies'])} replies")
    comment_loaded = mr.load(Comment, comment_dumped)
    assert comment_loaded == comment
    print("✓ Self-referencing lists (comment tree) work!")

    print("\n=== 2. @mr.pre_load hooks ===")

    # Email normalization using decorator
    user_data = {"id": 1, "email": "  JOHN@EXAMPLE.COM  ", "username": "john"}
    normalized_user = mr.load(NormalizedUser, user_data)

    print(f"Original email: '{user_data['email']}'")
    print(f"Normalized email: '{normalized_user.email}'")
    assert normalized_user.email == "john@example.com"
    print("✓ @mr.pre_load hook normalized email!")

    print("\n=== 3. Custom datetime format ===")

    event = Event(
        id=1,
        name="Conference",
        scheduled_at=datetime.datetime(2024, 12, 25, 14, 30, 0),
    )

    event_dict = mr.dump(event)
    print(f"Custom datetime format:")
    print(f"  scheduled_at: {event_dict['scheduled_at']}")
    # Output: 2024-12-25 14:30:00 (custom format, not ISO)

    loaded_event = mr.load(Event, event_dict)
    assert loaded_event == event
    print("✓ Custom datetime format works!")

    print("\n=== 4. Structured validation errors with get_validation_field_errors ===")

    invalid_data = {
        "user_id": -1,  # Invalid: negative
        "email": "not-an-email",  # Invalid: bad format
        "age": 150,  # Invalid: too old
        "tags": ["valid", ""],  # Invalid: empty tag
    }

    try:
        mr.load(ValidationExample, invalid_data)
        print("ERROR: Should have raised ValidationError!")
    except m.ValidationError as e:
        print(f"ValidationError raised!")
        print(f"  Raw messages: {e.messages}")

        # Get structured field errors
        field_errors = mr.get_validation_field_errors(e)
        print(f"\n  Structured errors:")
        for err in field_errors:
            if err.nested_errors:
                print(f"    - {err.name}:")
                for nested in err.nested_errors:
                    print(f"        - {nested.name}: {nested.error}")
            else:
                print(f"    - {err.name}: {err.error}")

        # Check specific fields
        error_fields = {err.name for err in field_errors}
        assert "user_id" in error_fields
        assert "email" in error_fields
        assert "age" in error_fields
        assert "tags" in error_fields
        print("\n✓ Structured validation errors work!")

    print("\n=== 5. add_pre_load for programmatic hooks ===")

    # Hook was added above with add_pre_load
    data_lower = {"value": "hello"}
    loaded_data = mr.load(DataWithPreLoad, data_lower)

    print(f"Original value: '{data_lower['value']}'")
    print(f"Loaded value: '{loaded_data.value}'")
    assert loaded_data.value == "HELLO"
    print("✓ add_pre_load hook transformed value to uppercase!")

    print("\n=== 6. collections.abc types ===")

    # Can pass list, tuple, or any sequence
    collection_obj = CollectionTypes(
        items=["a", "b", "c"],  # list (Sequence)
        unique_items={1, 2, 3},  # set (Set)
        metadata={"key": "value"},  # dict (Mapping)
    )

    collection_dict = mr.dump(collection_obj)
    print(f"Collections with abc types:")
    print(f"  items: {collection_dict['items']}")
    print(f"  unique_items: {collection_dict['unique_items']}")
    print(f"  metadata: {collection_dict['metadata']}")

    loaded_collection = mr.load(CollectionTypes, collection_dict)
    # Note: Sequence becomes list, Set becomes set, Mapping becomes dict after load
    assert isinstance(loaded_collection.items, list)
    assert isinstance(loaded_collection.unique_items, set)
    assert isinstance(loaded_collection.metadata, dict)
    print("✓ collections.abc types work correctly!")

    print("\n=== 7. NewType support ===")

    user = UserWithNewType(
        user_id=UserId(42),  # NewType wrapping int
        email=Email("user@example.com"),  # NewType wrapping str
        name="John Doe",
    )

    user_dict = mr.dump(user)
    print(f"NewType fields:")
    print(f"  user_id: {user_dict['user_id']} (type: {type(user_dict['user_id'])})")
    print(f"  email: {user_dict['email']} (type: {type(user_dict['email'])})")

    # Load back - NewType is transparent at runtime
    loaded_user = mr.load(UserWithNewType, user_dict)
    assert loaded_user.user_id == 42
    assert loaded_user.email == "user@example.com"
    print("✓ NewType works (transparent at runtime)!")

    print("\n=== 8. Multiple validation errors at once ===")

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Nested:
        value: int

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container:
        field1: int
        field2: list[int]
        nested: Nested

    try:
        mr.load(
            Container,
            {
                "field1": "not_int",  # Error in field1
                "field2": ["not_int"],  # Error in field2[0]
                "nested": {"value": "not_int"},  # Error in nested.value
            },
        )
    except m.ValidationError as e:
        field_errors = mr.get_validation_field_errors(e)
        print(f"Multiple validation errors:")
        for err in field_errors:
            if err.nested_errors:
                print(f"  - {err.name}:")
                for nested in err.nested_errors:
                    if nested.nested_errors:
                        print(f"      - {nested.name}:")
                        for nn in nested.nested_errors:
                            print(f"          - {nn.name}: {nn.error}")
                    else:
                        print(f"      - {nested.name}: {nested.error}")
            else:
                print(f"  - {err.name}: {err.error}")

        print("✓ Multiple nested validation errors captured!")

    print("\n=== Summary ===")
    print("✓ Cyclic/self-referencing structures (parent references, comment trees)")
    print("✓ @mr.pre_load decorator for data transformation hooks")
    print("✓ Custom datetime formats with datetime_meta(format=...)")
    print("✓ Structured validation error handling with get_validation_field_errors()")
    print("✓ Programmatic hook addition with add_pre_load()")
    print("✓ collections.abc types (Sequence, Set, Mapping)")
    print("✓ NewType support (transparent at runtime)")
    print("✓ Complex nested validation error reporting")
