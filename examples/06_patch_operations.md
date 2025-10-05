# PATCH Operations

Using `mr.MISSING` to distinguish between null and missing fields in partial updates.

## The Problem

In PATCH operations, you need to distinguish:
- **Field not provided** - don't update
- **Field set to None** - explicitly clear the value
- **Field set to value** - update to new value

Standard Python optional fields can't distinguish between "not provided" and "explicitly None".

## Solution: mr.MISSING

Use `mr.MISSING` as the default value to detect unprovided fields:

```python
import dataclasses
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass
class UserProfilePatch:
    """Partial update model using mr.MISSING."""

    username: str = mr.MISSING
    email: str = mr.MISSING
    phone: str | None = mr.MISSING
    bio: str | None = mr.MISSING
    avatar_url: str | None = mr.MISSING
```

## Basic PATCH Usage

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserProfile:
    """Full user profile."""

    user_id: uuid.UUID
    username: str
    email: str
    phone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


# Original user
user = UserProfile(
    user_id=uuid.uuid4(),
    username="john_doe",
    email="john@example.com",
    phone="+1234567890",
    bio="Software developer",
    avatar_url="https://example.com/avatar.jpg",
)

# PATCH: Update only username
patch_data = {"username": "johndoe"}
patch = mr.load(UserProfilePatch, patch_data)

# patch.username == "johndoe"
# patch.email is mr.MISSING
# patch.phone is mr.MISSING
# patch.bio is mr.MISSING
# patch.avatar_url is mr.MISSING
```

## Applying PATCH Updates

Check for `mr.MISSING` to determine which fields to update:

```python
def apply_patch(original: UserProfile, patch_data: dict) -> UserProfile:
    """Apply PATCH update to user profile."""
    patch = mr.load(UserProfilePatch, patch_data)

    updates = {}
    if patch.username is not mr.MISSING:
        updates["username"] = patch.username
    if patch.email is not mr.MISSING:
        updates["email"] = patch.email
    if patch.phone is not mr.MISSING:
        updates["phone"] = patch.phone
    if patch.bio is not mr.MISSING:
        updates["bio"] = patch.bio
    if patch.avatar_url is not mr.MISSING:
        updates["avatar_url"] = patch.avatar_url

    return dataclasses.replace(original, **updates)


# Update only username
patched_user = apply_patch(user, {"username": "johndoe"})
# patched_user.username == "johndoe"
# patched_user.phone == "+1234567890" (unchanged)
```

## Explicitly Setting None

Distinguish between "not provided" and "explicitly None":

```python
# PATCH: Remove phone number (set to None)
patch_data = {"phone": None}
patch = mr.load(UserProfilePatch, patch_data)

# patch.username is mr.MISSING (not provided)
# patch.phone is None (explicitly set to None)

patched_user = apply_patch(user, {"phone": None})
# patched_user.phone is None (explicitly cleared)
# patched_user.username unchanged
```

## Dumping PATCH Objects

When dumping, `mr.MISSING` fields are excluded:

```python
patch = UserProfilePatch(username="new_name", bio=None)
dumped = mr.dump(patch)

# {
#     'username': 'new_name'
#     # email, phone, avatar_url not present (MISSING)
#     # bio not present (None excluded by default)
# }
```

## PATCH with none_value_handling=INCLUDE

To include None values in dumps (distinguish None from MISSING):

```python
import decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class CompanyInfoPatch:
    prohibited_business: bool | None = mr.MISSING
    cbd_business: bool | None = mr.MISSING
    sic_codes_inlines_nob: bool | None = mr.MISSING
    trading_address_has_business_evidences: bool | None = mr.MISSING


patch = CompanyInfoPatch(prohibited_business=None, cbd_business=True)
dumped = mr.dump(patch)

# {
#     'prohibited_business': None,  # Explicitly None
#     'cbd_business': True,          # Explicitly True
#     # sic_codes_inlines_nob not present (MISSING)
#     # trading_address_has_business_evidences not present (MISSING)
# }

# This allows three states:
# - Field not in dict → MISSING (don't update)
# - Field in dict with None → Explicitly clear
# - Field in dict with value → Update to value
```

## Real-World Pattern

```python
# API receives PATCH request
update_data_raw = {
    "cbd_business": True,
    # Other fields not provided, should stay unchanged
}

# Load as PATCH model
patch_obj = mr.load(CompanyInfoPatch, update_data_raw)

# Dump for database update
update_data = mr.dump(patch_obj)

# Only cbd_business in update_data
# Database UPDATE will only touch that field
# Other fields remain unchanged in database
```

## Key Principles

1. **Default to `mr.MISSING`** - All PATCH fields should default to `mr.MISSING`
2. **Check for `mr.MISSING`** - Use `is mr.MISSING` to detect unprovided fields
3. **Three states** - `mr.MISSING` (not provided), `None` (explicitly cleared), value (updated)
4. **MISSING excluded on dump** - `mr.MISSING` fields are never included in serialised output
5. **Use with INCLUDE** - Combine with `none_value_handling=INCLUDE` to distinguish None from MISSING
