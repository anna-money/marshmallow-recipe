# Generic Types

Working with `Generic[T]` dataclasses in marshmallow-recipe.

## Basic Generic Usage

```python
import dataclasses
from typing import Generic, TypeVar

import marshmallow_recipe as mr

T = TypeVar("T")


@dataclasses.dataclass
class SimpleContainer(Generic[T]):
    """Simple generic container (no frozen/slots)."""

    value: T


# Without frozen/slots, type can be inferred
simple_int = SimpleContainer(value=42)
simple_dumped = mr.dump(simple_int)

simple_loaded = mr.load(SimpleContainer[int], simple_dumped)
```

## frozen=True or slots=True Requires Explicit Type

**Important:** For dataclasses with `frozen=True` or `slots=True`, you **must** provide the explicit type to `dump()`:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class StrictContainer(Generic[T]):
    """Strict generic container."""

    value: T


strict_str = StrictContainer[str](value="hello")

# MUST pass type to dump
strict_dumped = mr.dump(StrictContainer[str], strict_str)

# MUST pass type to load
strict_loaded = mr.load(StrictContainer[str], strict_dumped)

# Without type - raises ValueError
# mr.dump(strict_str)  # ❌ Error!
```

## Nested Generics

Generic types can be nested:

```python
TValue = TypeVar("TValue")


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Result(Generic[TValue]):
    """Generic result type."""

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
    id: int
    name: str
    email: str


# Generic containing another generic
result_user = Result[User](
    success=True,
    value=User(id=1, name="John Doe", email="john@example.com"),
)

response = ApiResponse[User](request_id="req-123", result=result_user)

response_dumped = mr.dump(ApiResponse[User], response)
response_loaded = mr.load(ApiResponse[User], response_dumped)
```

## Reusing Generic with Different Types

The same generic type can be used with different type arguments:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PagedResponse(Generic[T]):
    """Generic paged API response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    id: int
    name: str
    price: float


# Same generic with different types
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

user_page_loaded = mr.load(PagedResponse[User], user_page_dumped)
product_page_loaded = mr.load(PagedResponse[Product], product_page_dumped)
```

## Generic Inheritance

Child classes can inherit from a concrete generic type:

```python
TItem = TypeVar("TItem")


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericParent(Generic[TItem]):
    """Parent generic class."""

    items: list[TItem]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericChild(GenericParent[int]):
    """Child class with specific type."""

    total: int


# Child is not generic anymore
child = GenericChild(items=[1, 2, 3], total=3)

child_dumped = mr.dump(child)  # No type argument needed
child_loaded = mr.load(GenericChild, child_dumped)
```

## Generic with Optional Fields

Generics work with optional and None values:

```python
# Error result (value is None)
error_result = Result[User](success=False, value=None, error="User not found")

error_response = ApiResponse[User](request_id="req-456", result=error_result)

error_dumped = mr.dump(ApiResponse[User], error_response)
# {
#     'request_id': 'req-456',
#     'result': {
#         'success': False,
#         'error': 'User not found'
#         # 'value' excluded (None)
#     }
# }

error_loaded = mr.load(ApiResponse[User], error_dumped)
# error_loaded.result.value is None
# error_loaded.result.error == "User not found"
```

## Key Takeaways

1. **Without frozen/slots**: `mr.dump(instance)` - type inferred
2. **With frozen/slots**: `mr.dump(Generic[Type], instance)` - type required
3. **Always provide type on load**: `mr.load(Generic[Type], data)`
4. **Nested generics** work seamlessly
5. **Generics can be reused** with different type arguments
6. **Inheritance from concrete generic** makes child non-generic
