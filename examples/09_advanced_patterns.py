"""
Advanced patterns in marshmallow-recipe.

This example demonstrates:
- BaseModel pattern with dump/load/schema methods
- Cyclic/self-referencing structures
- @mr.pre_load hooks for data transformation
- @mr.options(decimal_places=N) for global decimal precision
- @mr.options(none_value_handling=INCLUDE) for including None values
- Combining multiple advanced features
"""

import dataclasses
import decimal
from typing import Any, Self

from marshmallow import Schema

import marshmallow_recipe as mr


# ============================================================
# Pattern 1: BaseModel with convenience methods
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class BaseModel:
    """Base model with convenience serialization methods."""

    def dump(self) -> dict[str, Any]:
        """Serialize this model to dict."""
        return mr.dump(self)

    @classmethod
    def load(cls, data: dict[str, Any]) -> Self:
        """Deserialize dict to this model."""
        return mr.load(cls, data)

    @classmethod
    def load_many(cls, data: list[dict[str, Any]]) -> list[Self]:
        """Deserialize list of dicts to list of models."""
        return mr.load_many(cls, data)

    @classmethod
    def schema(cls, *, many: bool = False) -> Schema:
        """Get marshmallow schema for this model."""
        return mr.schema(cls, many=many)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Article(BaseModel):
    """Article using BaseModel pattern."""

    id: int
    title: str
    content: str
    author_id: int


# ============================================================
# Pattern 2: Cyclic/self-referencing structures
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
# Pattern 3: @mr.pre_load hooks
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NormalizedUser:
    """User with email normalization via pre_load."""

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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TimestampedModel:
    """Model with automatic timestamp extraction."""

    id: int
    data: str

    @staticmethod
    @mr.pre_load
    def extract_timestamp(data: dict[str, Any]) -> dict[str, Any]:
        """Extract timestamp from metadata if present."""
        if "metadata" in data and "timestamp" in data["metadata"]:
            # Transform nested timestamp to top-level field
            data = {**data, "created_at": data["metadata"]["timestamp"]}
        return data


# ============================================================
# Pattern 4: Global decimal_places with @mr.options
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=2)
class Price:
    """Price with 2 decimal places for all decimal fields."""

    amount: decimal.Decimal
    tax: decimal.Decimal
    discount: decimal.Decimal
    total: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Invoice:
    """Invoice without decimal_places option."""

    id: int
    amount: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=4)
class InvoiceContainer:
    """Container with decimal_places=4, but nested Invoice has default precision."""

    invoice: Invoice
    processing_fee: decimal.Decimal


# ============================================================
# Pattern 5: none_value_handling=INCLUDE
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class ApiResponse:
    """API response that explicitly includes None values."""

    status: str
    data: dict[str, Any] | None = None
    error: str | None = None
    warning: str | None = None


# ============================================================
# Pattern 6: Combining multiple features
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
    decimal_places=3,
)
class ComplexModel(BaseModel):
    """Model combining multiple @mr.options features."""

    user_id: int
    account_balance: decimal.Decimal
    last_login: str | None = None

    @staticmethod
    @mr.pre_load
    def sanitize(data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize data before loading."""
        # Convert empty strings to None
        return {k: (None if v == "" else v) for k, v in data.items()}


if __name__ == "__main__":
    print("=== Pattern 1: BaseModel with convenience methods ===")

    article = Article(id=1, title="Hello World", content="Article content", author_id=42)

    # Use instance method to serialize
    article_dict = article.dump()
    print(f"Serialized via .dump(): {article_dict}")

    # Use class method to deserialize
    loaded_article = Article.load(article_dict)
    assert loaded_article == article
    print("✓ BaseModel pattern provides clean API")

    # load_many example
    articles_list = Article.load_many([article_dict, article_dict])
    assert len(articles_list) == 2
    print(f"✓ Loaded {len(articles_list)} articles via .load_many()")

    print("\n=== Pattern 2: Cyclic/self-referencing structures ===")

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
    print(f"  - First reply has {len(comment_dumped['replies'][1]['replies'])} nested replies")

    comment_loaded = mr.load(Comment, comment_dumped)
    assert comment_loaded == comment
    print("✓ Self-referencing lists (comment tree) work!")

    print("\n=== Pattern 3: @mr.pre_load hooks ===")

    # Email normalization
    user_data = {"id": 1, "email": "  JOHN@EXAMPLE.COM  ", "username": "john"}
    normalized_user = mr.load(NormalizedUser, user_data)

    print(f"Original email: '{user_data['email']}'")
    print(f"Normalized email: '{normalized_user.email}'")
    assert normalized_user.email == "john@example.com"
    print("✓ pre_load hook normalized email!")

    print("\n=== Pattern 4: Global decimal_places ===")

    # All decimal fields get 2 places
    price = Price(
        amount=decimal.Decimal("100.12345"),
        tax=decimal.Decimal("20.6789"),
        discount=decimal.Decimal("5.999"),
        total=decimal.Decimal("115.8"),
    )

    price_dumped = mr.dump(price)
    print(f"Price with global decimal_places=2:")
    print(f"  - amount: {price_dumped['amount']}")
    print(f"  - tax: {price_dumped['tax']}")
    print(f"  - discount: {price_dumped['discount']}")

    assert price_dumped["amount"] == "100.12"
    assert price_dumped["tax"] == "20.68"
    assert price_dumped["discount"] == "6.00"
    print("✓ Global decimal_places applied to all fields!")

    # Nested decimal_places behavior
    invoice = Invoice(id=1, amount=decimal.Decimal("99.12345"))
    container = InvoiceContainer(
        invoice=invoice,
        processing_fee=decimal.Decimal("1.23456789"),
    )

    container_dumped = mr.dump(container)
    print(f"\nContainer with decimal_places=4:")
    print(f"  - processing_fee (4 places): {container_dumped['processing_fee']}")
    print(f"  - invoice.amount (default): {container_dumped['invoice']['amount']}")

    # Container has decimal_places=4, but nested Invoice has default precision (2)
    assert container_dumped["processing_fee"] == "1.2346"
    assert container_dumped["invoice"]["amount"] == "99.12"
    print("✓ Nested models keep their own decimal_places!")

    print("\n=== Pattern 5: none_value_handling=INCLUDE ===")

    # Success response with data
    success_response = ApiResponse(status="success", data={"result": 42}, error=None)
    success_dumped = mr.dump(success_response)

    print(f"Success response: {success_dumped}")
    assert "data" in success_dumped
    assert "error" in success_dumped  # None is included!
    assert success_dumped["error"] is None
    print("✓ None values included in output!")

    # Error response
    error_response = ApiResponse(status="error", data=None, error="Something went wrong")
    error_dumped = mr.dump(error_response)

    print(f"Error response: {error_dumped}")
    assert error_dumped["data"] is None
    assert error_dumped["error"] == "Something went wrong"
    print("✓ Explicit None vs actual value distinguished!")

    print("\n=== Pattern 6: Combining multiple features ===")

    # camelCase + INCLUDE + decimal_places + pre_load
    complex_data = {
        "userId": 1,
        "accountBalance": "123.456789",
        "lastLogin": "",  # Empty string will be converted to None by pre_load
    }

    complex_model = ComplexModel.load(complex_data)
    print(f"Loaded complex model:")
    print(f"  - user_id: {complex_model.user_id}")
    print(f"  - account_balance: {complex_model.account_balance}")
    print(f"  - last_login: {complex_model.last_login}")

    assert complex_model.last_login is None  # Empty string converted to None
    print("✓ pre_load hook converted empty string to None!")

    complex_dumped = complex_model.dump()
    print(f"\nDumped complex model: {complex_dumped}")
    assert "userId" in complex_dumped  # camelCase
    assert "lastLogin" in complex_dumped  # none_value_handling=INCLUDE
    assert complex_dumped["lastLogin"] is None
    assert complex_dumped["accountBalance"] == "123.457"  # decimal_places=3
    print("✓ All features work together: camelCase + INCLUDE + decimal_places + pre_load!")
