"""
Naming case conventions in marshmallow-recipe.

This example demonstrates:
- @mr.options(naming_case=...) decorator for class-level convention
- mr.CAMEL_CASE (snake_case → camelCase)
- mr.CAPITAL_CAMEL_CASE (snake_case → PascalCase)
- mr.UPPER_SNAKE_CASE (snake_case → UPPER_SNAKE_CASE)
- Per-call naming_case in load/dump/schema
- Nested dataclasses with different naming conventions
- Creating reusable serialization functions
"""

import dataclasses
import datetime
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    """User without naming convention (default snake_case)."""

    user_id: uuid.UUID
    user_name: str
    email_address: str
    is_active: bool
    created_at: datetime.datetime


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class ApiRequest:
    """API request with camelCase naming convention."""

    request_id: uuid.UUID
    user_id: uuid.UUID
    request_type: str
    request_data: dict
    created_at: datetime.datetime


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)
class GraphQLResponse:
    """GraphQL response with PascalCase naming convention."""

    response_id: uuid.UUID
    data_items: list[str]
    has_next_page: bool
    total_count: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    """Address without naming convention (default)."""

    street_name: str
    city_name: str
    postal_code: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class CustomerProfile:
    """Customer profile with camelCase, but nested Address keeps snake_case."""

    customer_id: uuid.UUID
    full_name: str
    shipping_address: Address  # Nested dataclass keeps its own convention


# Reusable serialization wrapper for external APIs
def dump_for_external_api(obj: object) -> dict:
    """Serialize object to camelCase for external API consumption."""
    return mr.dump(obj, naming_case=mr.CAMEL_CASE)


def load_from_external_api(cls: type, data: dict) -> object:
    """Deserialize object from camelCase external API data."""
    return mr.load(cls, data, naming_case=mr.CAMEL_CASE)


if __name__ == "__main__":
    print("=== Default snake_case ===")

    user = User(
        user_id=uuid.uuid4(),
        user_name="john_doe",
        email_address="john@example.com",
        is_active=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )

    user_dict = mr.dump(user)
    print(f"User (snake_case): {list(user_dict.keys())}")
    # Output: ['user_id', 'user_name', 'email_address', 'is_active', 'created_at']

    print("\n=== camelCase with @mr.options ===")

    api_request = ApiRequest(
        request_id=uuid.uuid4(),
        user_id=user.user_id,
        request_type="GET",
        request_data={"key": "value"},
        created_at=datetime.datetime.now(datetime.UTC),
    )

    request_dict = mr.dump(api_request)
    print(f"API Request (camelCase): {list(request_dict.keys())}")
    # Output: ['requestId', 'userId', 'requestType', 'requestData', 'createdAt']

    # Deserialize from camelCase
    loaded_request = mr.load(ApiRequest, request_dict)
    assert loaded_request == api_request
    print("✓ camelCase round-trip successful!")

    print("\n=== PascalCase with @mr.options ===")

    graphql_response = GraphQLResponse(
        response_id=uuid.uuid4(),
        data_items=["item1", "item2", "item3"],
        has_next_page=True,
        total_count=100,
    )

    response_dict = mr.dump(graphql_response)
    print(f"GraphQL Response (PascalCase): {list(response_dict.keys())}")
    # Output: ['ResponseId', 'DataItems', 'HasNextPage', 'TotalCount']

    loaded_response = mr.load(GraphQLResponse, response_dict)
    assert loaded_response == graphql_response
    print("✓ PascalCase round-trip successful!")

    print("\n=== Per-call naming_case override ===")

    # Override naming convention at call time
    user_camel = mr.dump(user, naming_case=mr.CAMEL_CASE)
    print(f"User with runtime camelCase: {list(user_camel.keys())}")
    # Output: ['userId', 'userName', 'emailAddress', 'isActive', 'createdAt']

    user_pascal = mr.dump(user, naming_case=mr.CAPITAL_CAMEL_CASE)
    print(f"User with runtime PascalCase: {list(user_pascal.keys())}")
    # Output: ['UserId', 'UserName', 'EmailAddress', 'IsActive', 'CreatedAt']

    user_upper = mr.dump(user, naming_case=mr.UPPER_SNAKE_CASE)
    print(f"User with runtime UPPER_SNAKE_CASE: {list(user_upper.keys())}")
    # Output: ['USER_ID', 'USER_NAME', 'EMAIL_ADDRESS', 'IS_ACTIVE', 'CREATED_AT']

    # Load back with the same convention
    loaded_user_camel = mr.load(User, user_camel, naming_case=mr.CAMEL_CASE)
    assert loaded_user_camel == user
    print("✓ Runtime naming_case override works!")

    print("\n=== Nested dataclasses with different conventions ===")

    address = Address(
        street_name="123 Main St",
        city_name="New York",
        postal_code="10001",
    )

    customer = CustomerProfile(
        customer_id=uuid.uuid4(),
        full_name="John Doe",
        shipping_address=address,
    )

    customer_dict = mr.dump(customer)
    print(f"Customer (camelCase):")
    print(f"  - Top-level keys: {list(customer_dict.keys())}")
    # Output: ['customerId', 'fullName', 'shippingAddress']
    print(f"  - Nested address keys: {list(customer_dict['shippingAddress'].keys())}")
    # Output: ['street_name', 'city_name', 'postal_code'] - keeps original convention!

    loaded_customer = mr.load(CustomerProfile, customer_dict)
    assert loaded_customer == customer
    print("✓ Nested dataclasses keep their own naming conventions!")

    print("\n=== Reusable serialization wrappers ===")

    # Use wrapper functions for consistent external API integration
    external_user_data = dump_for_external_api(user)
    print(f"Serialized for external API (camelCase): {list(external_user_data.keys())}")

    loaded_from_api = load_from_external_api(User, external_user_data)
    assert loaded_from_api == user
    print("✓ Reusable serialization wrappers work!")

    print("\n=== Schema generation with naming_case ===")

    # Schemas are cached per naming_case
    schema_default = mr.schema(User)
    schema_camel = mr.schema(User, naming_case=mr.CAMEL_CASE)

    print(f"Schema without naming_case: {schema_default}")
    print(f"Schema with camelCase: {schema_camel}")
    print(f"Schemas are different: {schema_default is not schema_camel}")
    print("✓ Schemas cached separately per naming_case!")
