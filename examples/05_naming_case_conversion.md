# Naming Case Conversion

Converting field names between different naming conventions.

## camelCase with @mr.options

Apply camelCase convention to all fields:

```python
import dataclasses
import datetime
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class ApiRequest:
    request_id: uuid.UUID
    user_id: uuid.UUID
    request_type: str
    request_data: dict
    created_at: datetime.datetime


api_request = ApiRequest(
    request_id=uuid.uuid4(),
    user_id=uuid.uuid4(),
    request_type="GET",
    request_data={"key": "value"},
    created_at=datetime.datetime.now(datetime.UTC),
)

request_dict = mr.dump(api_request)
# {
#     'requestId': '...',
#     'userId': '...',
#     'requestType': 'GET',
#     'requestData': {'key': 'value'},
#     'createdAt': '...'
# }

loaded_request = mr.load(ApiRequest, request_dict)
```

## PascalCase with @mr.options

Apply PascalCase convention (also called UpperCamelCase):

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)
class GraphQLResponse:
    response_id: uuid.UUID
    data_items: list[str]
    has_next_page: bool
    total_count: int


graphql_response = GraphQLResponse(
    response_id=uuid.uuid4(),
    data_items=["item1", "item2", "item3"],
    has_next_page=True,
    total_count=100,
)

response_dict = mr.dump(graphql_response)
# {
#     'ResponseId': '...',
#     'DataItems': ['item1', 'item2', 'item3'],
#     'HasNextPage': True,
#     'TotalCount': 100
# }
```

## Runtime naming_case Override

Override naming convention at call time:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    user_id: uuid.UUID
    user_name: str
    email_address: str
    is_active: bool


user = User(
    user_id=uuid.uuid4(),
    user_name="john_doe",
    email_address="john@example.com",
    is_active=True,
)

# Default: snake_case
default_dict = mr.dump(user)
# {'user_id': '...', 'user_name': 'john_doe', 'email_address': 'john@example.com', 'is_active': True}

# Runtime: camelCase
camel_dict = mr.dump(user, naming_case=mr.CAMEL_CASE)
# {'userId': '...', 'userName': 'john_doe', 'emailAddress': 'john@example.com', 'isActive': True}

# Runtime: PascalCase
pascal_dict = mr.dump(user, naming_case=mr.CAPITAL_CAMEL_CASE)
# {'UserId': '...', 'UserName': 'john_doe', 'EmailAddress': 'john@example.com', 'IsActive': True}

# Runtime: UPPER_SNAKE_CASE
upper_dict = mr.dump(user, naming_case=mr.UPPER_SNAKE_CASE)
# {'USER_ID': '...', 'USER_NAME': 'john_doe', 'EMAIL_ADDRESS': 'john@example.com', 'IS_ACTIVE': True}

# Load with the same convention
loaded_camel = mr.load(User, camel_dict, naming_case=mr.CAMEL_CASE)
```

## Nested Dataclasses Keep Their Own Conventions

Each dataclass maintains its own naming convention:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    street_name: str
    city_name: str
    postal_code: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class CustomerProfile:
    customer_id: uuid.UUID
    full_name: str
    shipping_address: Address  # Nested keeps snake_case


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
# {
#     'customerId': '...',
#     'fullName': 'John Doe',
#     'shippingAddress': {
#         'street_name': '123 Main St',    # Original snake_case preserved!
#         'city_name': 'New York',
#         'postal_code': '10001'
#     }
# }
```

## Reusable Serialisation Wrappers

Create helpers for consistent external API integration:

```python
def dump_for_external_api(obj: object) -> dict:
    """Serialise object to camelCase for external API consumption."""
    return mr.dump(obj, naming_case=mr.CAMEL_CASE)


def load_from_external_api(cls: type, data: dict) -> object:
    """Deserialise object from camelCase external API data."""
    return mr.load(cls, data, naming_case=mr.CAMEL_CASE)


# Usage
external_data = dump_for_external_api(user)
loaded = load_from_external_api(User, external_data)
```

## Schema Caching by naming_case

Schemas are cached separately for each naming convention:

```python
# Different schemas for different conventions
schema_default = mr.schema(User)
schema_camel = mr.schema(User, naming_case=mr.CAMEL_CASE)

# Schemas are different instances
# schema_default is not schema_camel
```

## Available Naming Conventions

- `mr.CAMEL_CASE` - snake_case → camelCase
- `mr.CAPITAL_CAMEL_CASE` - snake_case → PascalCase
- `mr.UPPER_SNAKE_CASE` - snake_case → UPPER_SNAKE_CASE
- Default (no option) - snake_case preserved
