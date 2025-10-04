"""
PATCH operations with mr.MISSING in marshmallow-recipe.

This example demonstrates:
- Using mr.MISSING to distinguish between null and missing fields
- PATCH vs PUT operations
- Partial updates with optional fields
- mr.MISSING with nested dataclasses
- mr.MISSING with collections
- Combining mr.MISSING with none_value_handling
"""

import dataclasses
import datetime
import decimal
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserProfile:
    """User profile for full updates (PUT)."""

    user_id: uuid.UUID
    username: str
    email: str
    phone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


@dataclasses.dataclass
class UserProfilePatch:
    """User profile for partial updates (PATCH).

    Using mr.MISSING allows distinguishing:
    - Field not provided in request (value = mr.MISSING)
    - Field explicitly set to None (value = None)
    - Field set to actual value (value = some_value)
    """

    username: str = mr.MISSING
    email: str = mr.MISSING
    phone: str | None = mr.MISSING
    bio: str | None = mr.MISSING
    avatar_url: str | None = mr.MISSING


@dataclasses.dataclass
class AccountSettingsPatch:
    """Account settings for PATCH with nested data."""

    email_notifications: bool = mr.MISSING
    sms_notifications: bool = mr.MISSING
    marketing_emails: bool = mr.MISSING
    theme: str = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class CompanyInfoPatch:
    """Company info PATCH model (from production code)."""

    prohibited_business: bool | None = mr.MISSING
    cbd_business: bool | None = mr.MISSING
    sic_codes_inlines_nob: bool | None = mr.MISSING
    trading_address_has_business_evidences: bool | None = mr.MISSING


def apply_patch(original: UserProfile, patch_data: dict) -> UserProfile:
    """
    Apply PATCH update to user profile.

    Only fields present in patch_data are updated.
    Fields with mr.MISSING value are not updated.
    """
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


if __name__ == "__main__":
    print("=== Problem: Distinguishing null from missing ===")

    # Original user profile
    user = UserProfile(
        user_id=uuid.uuid4(),
        username="john_doe",
        email="john@example.com",
        phone="+1234567890",
        bio="Software developer",
        avatar_url="https://example.com/avatar.jpg",
    )

    print(f"Original user:")
    print(f"  - phone: {user.phone}")
    print(f"  - bio: {user.bio}")

    print("\n=== PATCH: Update only username ===")

    # PATCH request: only update username
    patch_data_1 = {"username": "johndoe"}
    patched_user_1 = apply_patch(user, patch_data_1)

    print(f"After PATCH (username only):")
    print(f"  - username changed: {user.username} → {patched_user_1.username}")
    print(f"  - phone unchanged: {patched_user_1.phone}")
    print(f"  - bio unchanged: {patched_user_1.bio}")

    print("\n=== PATCH: Explicitly set phone to None ===")

    # PATCH request: remove phone number (set to None)
    patch_data_2 = {"phone": None}
    patched_user_2 = apply_patch(patched_user_1, patch_data_2)

    print(f"After PATCH (phone=None):")
    print(f"  - username unchanged: {patched_user_2.username}")
    print(f"  - phone removed: {user.phone} → {patched_user_2.phone}")
    print(f"  - bio unchanged: {patched_user_2.bio}")

    print("\n=== PATCH: Update bio, leave phone as None ===")

    # PATCH request: update bio, don't touch phone
    patch_data_3 = {"bio": "Senior Software Engineer"}
    patched_user_3 = apply_patch(patched_user_2, patch_data_3)

    print(f"After PATCH (bio only):")
    print(f"  - username unchanged: {patched_user_3.username}")
    print(f"  - phone still None: {patched_user_3.phone}")
    print(f"  - bio updated: {patched_user_2.bio} → {patched_user_3.bio}")

    print("\n=== How mr.MISSING works ===")

    # Load empty PATCH - all fields are MISSING
    empty_patch = mr.load(UserProfilePatch, {})
    print(f"Empty PATCH object:")
    print(f"  - username is MISSING: {empty_patch.username is mr.MISSING}")
    print(f"  - email is MISSING: {empty_patch.email is mr.MISSING}")

    # Load PATCH with null value
    null_patch = mr.load(UserProfilePatch, {"phone": None})
    print(f"\nPATCH with phone=null:")
    print(f"  - username is MISSING: {null_patch.username is mr.MISSING}")
    print(f"  - phone is None: {null_patch.phone is None}")
    print(f"  - phone is MISSING: {null_patch.phone is mr.MISSING}")

    # Load PATCH with actual value
    value_patch = mr.load(UserProfilePatch, {"bio": "New bio"})
    print(f"\nPATCH with bio value:")
    print(f"  - username is MISSING: {value_patch.username is mr.MISSING}")
    print(f"  - bio has value: {value_patch.bio}")
    print(f"  - bio is MISSING: {value_patch.bio is mr.MISSING}")

    print("\n=== Dumping PATCH objects ===")

    # When dumping, MISSING fields are excluded
    patch_to_dump = UserProfilePatch(username="new_name", bio=None)
    dumped_patch = mr.dump(patch_to_dump)

    print(f"Dumped PATCH:")
    print(f"  - Contains username: {'username' in dumped_patch}")
    print(f"  - Contains email: {'email' in dumped_patch}")  # MISSING, excluded
    print(f"  - Contains bio: {'bio' in dumped_patch}")  # None is excluded by default
    print(f"  - Dumped dict: {dumped_patch}")

    print("\n=== PATCH with none_value_handling=INCLUDE ===")

    # With INCLUDE, None values are included in dump
    company_patch_1 = CompanyInfoPatch(prohibited_business=None, cbd_business=True)
    dumped_company_1 = mr.dump(company_patch_1)

    print(f"Company PATCH (with INCLUDE):")
    print(f"  - prohibited_business (None): {dumped_company_1.get('prohibited_business')}")
    print(f"  - cbd_business (True): {dumped_company_1.get('cbd_business')}")
    print(f"  - sic_codes_inlines_nob (MISSING): {'sic_codes_inlines_nob' in dumped_company_1}")
    print(f"  - Dumped dict: {dumped_company_1}")

    # This allows distinguishing between:
    # - Field not provided (MISSING) - not in dict
    # - Field set to None - in dict with null value
    # - Field set to value - in dict with that value

    print("\n=== Real-world use case: Workstation update ===")

    # Simulate workstation update from production code
    update_data_raw = {
        "cbd_business": True,
        # Other fields not provided, should stay unchanged
    }

    patch_obj = mr.load(CompanyInfoPatch, update_data_raw)
    update_data = mr.dump(patch_obj)

    print(f"Update data to send to DB:")
    print(f"  - cbd_business in data: {'cbd_business' in update_data}")
    print(f"  - prohibited_business in data: {'prohibited_business' in update_data}")

    # Only cbd_business will be in update_data, so DB update will only touch that field
    # This is exactly how anna-checklist workstation updates work!
    print("✓ PATCH with mr.MISSING enables partial updates correctly!")
