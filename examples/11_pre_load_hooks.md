# Pre-Load Hooks

Data transformation before deserialisation using `@mr.pre_load` decorator.

## Basic @mr.pre_load Usage

Transform data before it's loaded into dataclass:

```python
import dataclasses
from typing import Any

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NormalisedUser:
    """User with email normalisation via @mr.pre_load."""

    id: int
    email: str
    username: str

    @staticmethod
    @mr.pre_load
    def normalise_email(data: dict[str, Any]) -> dict[str, Any]:
        """Normalise email to lowercase before loading."""
        if "email" in data:
            data = {**data, "email": data["email"].lower().strip()}
        return data


# Email normalisation
user_data = {"id": 1, "email": "  JOHN@EXAMPLE.COM  ", "username": "john"}
normalised_user = mr.load(NormalisedUser, user_data)

# normalised_user.email == "john@example.com"
# Lowercased and whitespace stripped automatically
```

## Multiple @mr.pre_load Hooks

Multiple hooks are applied in order:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CleanedProduct:
    """Product with multiple pre-load transformations."""

    name: str
    price: float
    category: str

    @staticmethod
    @mr.pre_load
    def strip_whitespace(data: dict[str, Any]) -> dict[str, Any]:
        """Strip whitespace from all string fields."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = value.strip()
            else:
                result[key] = value
        return result

    @staticmethod
    @mr.pre_load
    def normalise_category(data: dict[str, Any]) -> dict[str, Any]:
        """Normalise category to lowercase."""
        if "category" in data:
            data = {**data, "category": data["category"].lower()}
        return data


# Both hooks are applied
product_data = {"name": "  Gaming Laptop  ", "price": 999.99, "category": "  ELECTRONICS  "}
cleaned_product = mr.load(CleanedProduct, product_data)

# cleaned_product.name == "Gaming Laptop" (whitespace stripped)
# cleaned_product.category == "electronics" (lowercased and stripped)
```

## Default Values with Pre-Load

Apply default values if not provided:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ConfigWithDefaults:
    """Configuration with default values applied via pre-load."""

    name: str
    timeout: int
    retries: int

    @staticmethod
    @mr.pre_load
    def apply_defaults(data: dict[str, Any]) -> dict[str, Any]:
        """Apply default values if not provided."""
        defaults = {"timeout": 30, "retries": 3}
        return {**defaults, **data}


# Minimal data (defaults will be applied)
config_minimal = {"name": "production"}
loaded_config_minimal = mr.load(ConfigWithDefaults, config_minimal)

# loaded_config_minimal.timeout == 30 (default)
# loaded_config_minimal.retries == 3 (default)

# Override some defaults
config_custom = {"name": "staging", "timeout": 60}
loaded_config_custom = mr.load(ConfigWithDefaults, config_custom)

# loaded_config_custom.timeout == 60 (custom)
# loaded_config_custom.retries == 3 (default)
```

## Programmatic Hook with add_pre_load()

Add hooks without decorator:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DataWithProgrammaticHook:
    """Dataclass with programmatically added hook."""

    value: str


# Define hook function
def uppercase_transform(data: dict[str, Any]) -> dict[str, Any]:
    """Transform value to uppercase."""
    if "value" in data:
        data = {**data, "value": data["value"].upper()}
    return data


# Add hook programmatically
mr.add_pre_load(DataWithProgrammaticHook, uppercase_transform)

# Hook is applied
data_lower = {"value": "hello world"}
loaded_data = mr.load(DataWithProgrammaticHook, data_lower)

# loaded_data.value == "HELLO WORLD"
```

## API Request Normalisation

Practical example for API request handling:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ApiRequest:
    """API request with data cleanup."""

    endpoint: str
    method: str
    headers: dict[str, str]

    @staticmethod
    @mr.pre_load
    def normalise_method(data: dict[str, Any]) -> dict[str, Any]:
        """Normalise HTTP method to uppercase."""
        if "method" in data:
            data = {**data, "method": data["method"].upper()}
        return data

    @staticmethod
    @mr.pre_load
    def add_default_headers(data: dict[str, Any]) -> dict[str, Any]:
        """Add default headers if not provided."""
        default_headers = {"Content-Type": "application/json"}
        if "headers" in data:
            data = {**data, "headers": {**default_headers, **data["headers"]}}
        else:
            data = {**data, "headers": default_headers}
        return data


request_data = {"endpoint": "/api/users", "method": "post"}  # No headers provided
request = mr.load(ApiRequest, request_data)

# request.method == "POST" (normalised)
# request.headers == {"Content-Type": "application/json"} (default added)
```

## Common Use Cases

Pre-load hooks are useful for:

1. **Normalisation** - Convert data to standard format (lowercase emails, uppercase codes)
2. **Default values** - Apply defaults before validation
3. **Cleanup** - Strip whitespace, remove unwanted characters
4. **Data migration** - Transform legacy format to new format
5. **Validation prep** - Prepare data for validation (e.g., normalise before pattern matching)
6. **Field mapping** - Rename fields or restructure data
7. **Type coercion** - Convert string booleans to actual booleans

## Important Notes

1. **Signature**: Hook functions must have signature `(dict[str, Any]) -> dict[str, Any]`
2. **Decorator order**: Hooks are applied top to bottom (first decorator = first applied)
3. **Immutability**: Always return new dict, don't modify original: `data = {**data, "key": value}`
4. **Multiple hooks**: Multiple `@mr.pre_load` decorators work together
5. **Programmatic addition**: Use `mr.add_pre_load(cls, func)` to add hooks at runtime
6. **Before validation**: Hooks run **before** field validation, allowing cleanup before checks
7. **Marshmallow only**: Pre-load hooks only work with `mr.load()` (marshmallow-based), not with `mr.nuked.load()`. Using `@mr.pre_load` on a dataclass passed to `mr.nuked.load()` will raise a `TypeError`
