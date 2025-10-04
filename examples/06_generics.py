"""
Generic types in marshmallow-recipe.

This example demonstrates:
- Basic Generic[T] usage
- Generic with frozen=True/slots=True requires explicit type
- Nested generics
- Generic inheritance
- Reusing Generic with different type arguments
- Generic with field overrides in subclasses
"""

import dataclasses
from typing import Generic, TypeVar

import marshmallow_recipe as mr

T = TypeVar("T")
TValue = TypeVar("TValue")
TItem = TypeVar("TItem")


@dataclasses.dataclass
class SimpleContainer(Generic[T]):
    """Simple generic container (no frozen/slots)."""

    value: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class StrictContainer(Generic[T]):
    """Strict generic container (frozen=True, slots=True)."""

    value: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PagedResponse(Generic[T]):
    """Generic paged API response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Result(Generic[TValue]):
    """Generic result type (success or error)."""

    success: bool
    value: TValue | None = None
    error: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ApiResponse(Generic[T]):
    """API response wrapping result."""

    request_id: str
    result: Result[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    """User model (not generic)."""

    id: int
    name: str
    email: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    """Product model (not generic)."""

    id: int
    name: str
    price: float


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericParent(Generic[TItem]):
    """Parent generic class."""

    items: list[TItem]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericChild(GenericParent[int]):
    """Child class with specific type."""

    total: int


if __name__ == "__main__":
    print("=== Simple generic (no frozen/slots) ===")

    # Without frozen/slots, type can be inferred
    simple_int = SimpleContainer(value=42)
    simple_dumped = mr.dump(simple_int)
    print(f"Simple container[int]: {simple_dumped}")

    simple_loaded = mr.load(SimpleContainer[int], simple_dumped)
    assert simple_loaded.value == 42
    print("✓ Simple generic works without explicit type on dump")

    print("\n=== Strict generic (frozen=True, slots=True) ===")

    # With frozen/slots, must provide explicit type on dump
    strict_str = StrictContainer[str](value="hello")

    # MUST pass type to dump
    strict_dumped = mr.dump(StrictContainer[str], strict_str)
    print(f"Strict container[str]: {strict_dumped}")

    # MUST pass type to load
    strict_loaded = mr.load(StrictContainer[str], strict_dumped)
    assert strict_loaded.value == "hello"
    print("✓ Strict generic requires explicit type for frozen/slots")

    # Without type - will raise error
    try:
        mr.dump(strict_str)  # Missing type!
        print("ERROR: Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Caught error: {str(e)[:60]}...")

    print("\n=== Nested generics ===")

    # Generic containing another generic
    result_user = Result[User](
        success=True,
        value=User(id=1, name="John Doe", email="john@example.com"),
        error=None,
    )

    response = ApiResponse[User](request_id="req-123", result=result_user)

    response_dumped = mr.dump(ApiResponse[User], response)
    print(f"API response with nested generics:")
    print(f"  - request_id: {response_dumped['request_id']}")
    print(f"  - result.value.name: {response_dumped['result']['value']['name']}")

    response_loaded = mr.load(ApiResponse[User], response_dumped)
    assert response_loaded == response
    print("✓ Nested generics work correctly!")

    print("\n=== Reusing Generic with different types ===")

    # Same generic type with different type arguments
    user_page = PagedResponse[User](
        items=[
            User(id=1, name="Alice", email="alice@example.com"),
            User(id=2, name="Bob", email="bob@example.com"),
        ],
        total=100,
        page=1,
        page_size=2,
        has_next=True,
    )

    product_page = PagedResponse[Product](
        items=[
            Product(id=1, name="Laptop", price=999.99),
            Product(id=2, name="Mouse", price=29.99),
        ],
        total=50,
        page=1,
        page_size=2,
        has_next=True,
    )

    user_page_dumped = mr.dump(PagedResponse[User], user_page)
    product_page_dumped = mr.dump(PagedResponse[Product], product_page)

    print(f"User page: {len(user_page_dumped['items'])} users")
    print(f"Product page: {len(product_page_dumped['items'])} products")

    user_page_loaded = mr.load(PagedResponse[User], user_page_dumped)
    product_page_loaded = mr.load(PagedResponse[Product], product_page_dumped)

    assert user_page_loaded == user_page
    assert product_page_loaded == product_page
    print("✓ Same generic reused with different types!")

    print("\n=== Generic inheritance ===")

    # Child class inheriting from Generic[int]
    child = GenericChild(items=[1, 2, 3], total=3)

    child_dumped = mr.dump(child)
    print(f"Generic child: {child_dumped}")

    child_loaded = mr.load(GenericChild, child_dumped)
    assert child_loaded == child
    print("✓ Generic inheritance works!")

    print("\n=== Error result (Generic with None) ===")

    # Result with error (value is None)
    error_result = Result[User](success=False, value=None, error="User not found")

    error_response = ApiResponse[User](request_id="req-456", result=error_result)

    error_dumped = mr.dump(ApiResponse[User], error_response)
    print(f"Error response:")
    print(f"  - success: {error_dumped['result']['success']}")
    print(f"  - error: {error_dumped['result'].get('error')}")
    print(f"  - value present: {'value' in error_dumped['result']}")

    error_loaded = mr.load(ApiResponse[User], error_dumped)
    assert error_loaded.result.value is None
    assert error_loaded.result.error == "User not found"
    print("✓ Generic with Optional fields works!")

    print("\n=== Key takeaways ===")
    print("1. Without frozen/slots: mr.dump(instance) - type inferred")
    print("2. With frozen/slots: mr.dump(Generic[Type], instance) - type required")
    print("3. Always provide type on load: mr.load(Generic[Type], data)")
    print("4. Nested generics work seamlessly")
    print("5. Generics can be reused with different type arguments")
