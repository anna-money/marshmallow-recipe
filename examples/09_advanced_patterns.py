"""
Per-dataclass customization with @mr.options decorator.

This example demonstrates:
- @mr.options(naming_case=...) for field name conversion
- @mr.options(none_value_handling=...) for None value control
- @mr.options(decimal_places=N) for decimal precision
- Combining multiple @mr.options parameters
- How @mr.options applies to a specific dataclass (not inherited by nested classes)
"""

import dataclasses
import decimal
import uuid

import marshmallow_recipe as mr


# ============================================================
# Pattern 1: naming_case per dataclass
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SnakeCaseModel:
    """Default naming (snake_case)."""

    user_id: int
    user_name: str
    email_address: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAMEL_CASE)
class CamelCaseModel:
    """camelCase naming."""

    user_id: int
    user_name: str
    email_address: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)
class PascalCaseModel:
    """PascalCase naming."""

    user_id: int
    user_name: str
    email_address: str


# ============================================================
# Pattern 2: none_value_handling per dataclass
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DefaultNoneHandling:
    """Default: None values excluded (IGNORE)."""

    required_field: str
    optional_field: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class IncludeNoneHandling:
    """Explicitly include None values."""

    required_field: str
    optional_field: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(none_value_handling=mr.NoneValueHandling.IGNORE)
class IgnoreNoneHandling:
    """Explicitly exclude None values."""

    required_field: str
    optional_field: str | None = None


# ============================================================
# Pattern 3: decimal_places per dataclass
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DefaultDecimalPrecision:
    """Default decimal precision (2 places)."""

    amount: decimal.Decimal
    rate: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=4)
class HighDecimalPrecision:
    """High precision (4 places)."""

    amount: decimal.Decimal
    rate: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(decimal_places=9)
class VeryHighDecimalPrecision:
    """Very high precision (9 places) for forex/crypto."""

    amount: decimal.Decimal
    rate: decimal.Decimal


# ============================================================
# Pattern 4: Combining multiple @mr.options
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
)
class CombinedOptionsV1:
    """Combine naming + none handling."""

    user_id: int
    last_login: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAPITAL_CAMEL_CASE,
    decimal_places=3,
)
class CombinedOptionsV2:
    """Combine naming + decimal precision."""

    account_balance: decimal.Decimal
    interest_rate: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    none_value_handling=mr.NoneValueHandling.INCLUDE,
    decimal_places=4,
)
class AllOptionsModel:
    """Combine all three options."""

    transaction_id: uuid.UUID
    amount_usd: decimal.Decimal
    exchange_rate: decimal.Decimal
    error_message: str | None = None


# ============================================================
# Pattern 5: Options NOT inherited by nested classes
# ============================================================


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class InnerModel:
    """Nested model WITHOUT @mr.options."""

    inner_field: str
    inner_amount: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
@mr.options(
    naming_case=mr.CAMEL_CASE,
    decimal_places=4,
)
class OuterModel:
    """Outer model WITH @mr.options."""

    outer_field: str
    outer_amount: decimal.Decimal
    nested: InnerModel  # InnerModel keeps its own settings!


if __name__ == "__main__":
    print("=== Pattern 1: naming_case per dataclass ===")

    # Same data, different naming conventions
    snake_model = SnakeCaseModel(user_id=1, user_name="john", email_address="john@example.com")
    snake_dict = mr.dump(snake_model)
    print(f"SnakeCaseModel: {list(snake_dict.keys())}")
    # ['user_id', 'user_name', 'email_address']

    camel_model = CamelCaseModel(user_id=1, user_name="john", email_address="john@example.com")
    camel_dict = mr.dump(camel_model)
    print(f"CamelCaseModel: {list(camel_dict.keys())}")
    # ['userId', 'userName', 'emailAddress']

    pascal_model = PascalCaseModel(user_id=1, user_name="john", email_address="john@example.com")
    pascal_dict = mr.dump(pascal_model)
    print(f"PascalCaseModel: {list(pascal_dict.keys())}")
    # ['UserId', 'UserName', 'EmailAddress']

    print("✓ Each dataclass has its own naming convention!")

    print("\n=== Pattern 2: none_value_handling per dataclass ===")

    # Default: None values excluded
    default_model = DefaultNoneHandling(required_field="test", optional_field=None)
    default_dict = mr.dump(default_model)
    print(f"Default (IGNORE): 'optional_field' present = {'optional_field' in default_dict}")
    # False - None excluded

    # INCLUDE: None values included
    include_model = IncludeNoneHandling(required_field="test", optional_field=None)
    include_dict = mr.dump(include_model)
    print(f"INCLUDE: 'optional_field' present = {'optional_field' in include_dict}")
    print(f"  Value: {include_dict.get('optional_field')}")
    # True - None included

    # Explicit IGNORE
    ignore_model = IgnoreNoneHandling(required_field="test", optional_field=None)
    ignore_dict = mr.dump(ignore_model)
    print(f"Explicit IGNORE: 'optional_field' present = {'optional_field' in ignore_dict}")
    # False - None excluded

    print("✓ Each dataclass controls its own None handling!")

    print("\n=== Pattern 3: decimal_places per dataclass ===")

    # Default: 2 decimal places
    default_decimal = DefaultDecimalPrecision(
        amount=decimal.Decimal("123.456789"),
        rate=decimal.Decimal("0.123456789"),
    )
    default_decimal_dict = mr.dump(default_decimal)
    print(f"Default (2 places):")
    print(f"  amount: {default_decimal_dict['amount']}")
    print(f"  rate: {default_decimal_dict['rate']}")
    # amount: 123.46, rate: 0.12

    # High precision: 4 decimal places
    high_precision = HighDecimalPrecision(
        amount=decimal.Decimal("123.456789"),
        rate=decimal.Decimal("0.123456789"),
    )
    high_precision_dict = mr.dump(high_precision)
    print(f"High precision (4 places):")
    print(f"  amount: {high_precision_dict['amount']}")
    print(f"  rate: {high_precision_dict['rate']}")
    # amount: 123.4568, rate: 0.1235

    # Very high precision: 9 decimal places
    very_high_precision = VeryHighDecimalPrecision(
        amount=decimal.Decimal("123.456789123"),
        rate=decimal.Decimal("0.123456789123"),
    )
    very_high_precision_dict = mr.dump(very_high_precision)
    print(f"Very high precision (9 places):")
    print(f"  amount: {very_high_precision_dict['amount']}")
    print(f"  rate: {very_high_precision_dict['rate']}")
    # amount: 123.456789123, rate: 0.123456789

    print("✓ Each dataclass has its own decimal precision!")

    print("\n=== Pattern 4: Combining multiple @mr.options ===")

    # Combine naming + none handling
    combined_v1 = CombinedOptionsV1(user_id=1, last_login=None)
    combined_v1_dict = mr.dump(combined_v1)
    print(f"camelCase + INCLUDE:")
    print(f"  Keys: {list(combined_v1_dict.keys())}")
    print(f"  lastLogin: {combined_v1_dict['lastLogin']}")
    # ['userId', 'lastLogin'], lastLogin: None

    # Combine naming + decimal precision
    combined_v2 = CombinedOptionsV2(
        account_balance=decimal.Decimal("1234.56789"),
        interest_rate=decimal.Decimal("0.123456"),
    )
    combined_v2_dict = mr.dump(combined_v2)
    print(f"\nPascalCase + 3 decimal places:")
    print(f"  Keys: {list(combined_v2_dict.keys())}")
    print(f"  AccountBalance: {combined_v2_dict['AccountBalance']}")
    print(f"  InterestRate: {combined_v2_dict['InterestRate']}")
    # ['AccountBalance', 'InterestRate'], AccountBalance: 1234.568, InterestRate: 0.123

    # Combine all three
    all_options = AllOptionsModel(
        transaction_id=uuid.uuid4(),
        amount_usd=decimal.Decimal("99.123456789"),
        exchange_rate=decimal.Decimal("1.23456789"),
        error_message=None,
    )
    all_options_dict = mr.dump(all_options)
    print(f"\ncamelCase + INCLUDE + 4 decimal places:")
    print(f"  Keys: {list(all_options_dict.keys())}")
    print(f"  amountUsd: {all_options_dict['amountUsd']}")
    print(f"  errorMessage: {all_options_dict['errorMessage']}")
    # ['transactionId', 'amountUsd', 'exchangeRate', 'errorMessage']
    # amountUsd: 99.1235, errorMessage: None

    print("✓ All @mr.options parameters work together!")

    print("\n=== Pattern 5: Options NOT inherited by nested classes ===")

    inner = InnerModel(
        inner_field="test",
        inner_amount=decimal.Decimal("123.456789"),
    )
    outer = OuterModel(
        outer_field="outer",
        outer_amount=decimal.Decimal("999.123456"),
        nested=inner,
    )

    outer_dict = mr.dump(outer)
    print(f"Outer model (camelCase, 4 places):")
    print(f"  Top-level keys: {list(outer_dict.keys())}")
    print(f"  outerAmount: {outer_dict['outerAmount']}")
    # ['outerField', 'outerAmount', 'nested']
    # outerAmount: 999.1235

    print(f"\nNested model (default snake_case, 2 places):")
    print(f"  Nested keys: {list(outer_dict['nested'].keys())}")
    print(f"  inner_amount: {outer_dict['nested']['inner_amount']}")
    # ['inner_field', 'inner_amount']
    # inner_amount: 123.46

    assert "outerField" in outer_dict  # camelCase from outer
    assert outer_dict["outerAmount"] == "999.1235"  # 4 places from outer
    assert "inner_field" in outer_dict["nested"]  # snake_case from inner (NOT camelCase!)
    assert outer_dict["nested"]["inner_amount"] == "123.46"  # 2 places from inner (NOT 4!)

    print("✓ Nested models keep their own @mr.options settings!")

    print("\n=== Summary ===")
    print("@mr.options decorator allows per-dataclass customization:")
    print("✓ naming_case: CAMEL_CASE, CAPITAL_CAMEL_CASE, UPPER_SNAKE_CASE")
    print("✓ none_value_handling: INCLUDE or IGNORE")
    print("✓ decimal_places: 2, 3, 4, 9, or any number")
    print("✓ Combine multiple options in one decorator")
    print("✓ Nested dataclasses keep their own settings (NOT inherited)")
