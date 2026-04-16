import collections.abc
import decimal
from typing import Any, TypeGuard, final

from .missing import MISSING
from .utils import (
    validate_datetime_format,
    validate_decimal_bound,
    validate_decimal_places,
    validate_decimal_rounding,
    validate_float_bound,
    validate_int_bound,
    validate_length_bound,
    validate_str_regexp,
)
from .validation import ValidationFunc


@final
class Metadata(collections.abc.Mapping[str, Any], collections.abc.Hashable):
    __slots__ = ("__values",)

    def __init__(self, values: collections.abc.Mapping[str, Any]) -> None:
        self.__values = values

    def __getitem__(self, key: str) -> Any:
        return self.__values[key]

    def __iter__(self) -> collections.abc.Iterator[str]:
        return iter(self.__values)

    def __len__(self) -> int:
        return len(self.__values)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__values})"

    def __str__(self) -> str:
        return str(self.__values)

    def __hash__(self) -> int:
        result = 0
        for key in self.__values:
            result ^= hash(key)
        return result ^ len(self.__values)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Metadata) and self.__values == other.__values


EMPTY_METADATA = Metadata({})


def is_metadata(value: Any) -> TypeGuard[Metadata]:
    return isinstance(value, Metadata)


def build_metadata(*, name: str, default: Any = MISSING, field_metadata: collections.abc.Mapping[Any, Any]) -> Metadata:
    """
    Build metadata dict from field info, allowing user metadata to override defaults.

    Used internally by bake and json_schema to merge computed values with user-provided metadata.
    The name and optional default are set first, then field_metadata overwrites if user provided custom values.
    """
    values: dict[str, Any] = {"name": name, "default": default}
    values.update({k: v for k, v in field_metadata.items() if isinstance(k, str)})
    return Metadata(values)


def metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure field serialization. Use via ``Annotated`` type hints.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        validate: Validation function or list of functions applied on load.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if validate is not None:
        values.update(validate=validate)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def str_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    min_length: int | None = None,
    min_length_error: str | None = None,
    max_length: int | None = None,
    max_length_error: str | None = None,
    regexp: str | None = None,
    regexp_error: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    strip_whitespaces: bool | None = None,
    post_load: collections.abc.Callable[[str], str] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure string field serialization with length and regexp validation.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        min_length: Minimum string length (character count).
        min_length_error: Custom error for min_length violation. Supports ``{min}`` placeholder.
        max_length: Maximum string length (character count).
        max_length_error: Custom error for max_length violation. Supports ``{max}`` placeholder.
        regexp: Regular expression pattern the string must match (from the start, like ``re.match``).
        regexp_error: Custom error when regexp validation fails.
        validate: Validation function or list of functions applied on load.
        strip_whitespaces: If True, strip leading/trailing whitespace on load.
        post_load: Callable applied to the string value after deserialization.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    validate_length_bound(min_length, "min_length")
    validate_length_bound(max_length, "max_length")
    validate_str_regexp(regexp)
    if min_length is not None and max_length is not None and min_length > max_length:
        raise ValueError(f"min_length {min_length} must be less than or equal to max_length {max_length}")
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if min_length is not None:
        values.update(min_length=min_length)
    if min_length_error is not None:
        values.update(min_length_error=min_length_error.format(min=min_length))
    if max_length is not None:
        values.update(max_length=max_length)
    if max_length_error is not None:
        values.update(max_length_error=max_length_error.format(max=max_length))
    if regexp is not None:
        values.update(regexp=regexp)
    if regexp_error is not None:
        values.update(regexp_error=regexp_error)
    if validate is not None:
        values.update(validate=validate)
    if strip_whitespaces is not None:
        values.update(strip_whitespaces=strip_whitespaces)
    if post_load is not None:
        values.update(post_load=post_load)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def decimal_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    places: int | None = MISSING,
    rounding: str | None = None,
    gt: decimal.Decimal | int | None = None,
    gt_error: str | None = None,
    gte: decimal.Decimal | int | None = None,
    gte_error: str | None = None,
    lt: decimal.Decimal | int | None = None,
    lt_error: str | None = None,
    lte: decimal.Decimal | int | None = None,
    lte_error: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure decimal field serialization with precision and range validation.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        places: Maximum decimal places. Raises ValidationError if exceeded.
        rounding: Rounding mode (e.g. ``decimal.ROUND_HALF_UP``).
            When set, rounds to ``places`` instead of validating.
        gt: Exclusive lower bound (>). Accepts Decimal or int.
        gt_error: Custom error for gt violation. Supports ``{min}`` placeholder.
        gte: Inclusive lower bound (>=). Accepts Decimal or int.
        gte_error: Custom error for gte violation. Supports ``{min}`` placeholder.
        lt: Exclusive upper bound (<). Accepts Decimal or int.
        lt_error: Custom error for lt violation. Supports ``{max}`` placeholder.
        lte: Inclusive upper bound (<=). Accepts Decimal or int.
        lte_error: Custom error for lte violation. Supports ``{max}`` placeholder.
        validate: Validation function or list of functions applied on load.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    validate_decimal_places(places)
    validate_decimal_rounding(rounding)
    validate_decimal_bound(gt, "gt")
    validate_decimal_bound(gte, "gte")
    validate_decimal_bound(lt, "lt")
    validate_decimal_bound(lte, "lte")
    if gt is not None and gte is not None:
        raise ValueError("gt and gte are mutually exclusive")
    if lt is not None and lte is not None:
        raise ValueError("lt and lte are mutually exclusive")
    lower = gt if gt is not None else gte
    upper = lt if lt is not None else lte
    if lower is not None and upper is not None:
        if gte is not None and lte is not None:
            if lower > upper:
                raise ValueError(f"lower bound {lower} must be less than or equal to upper bound {upper}")
        elif lower >= upper:
            raise ValueError(f"lower bound {lower} must be less than upper bound {upper}")
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if places is not MISSING:
        values.update(places=places)
    if rounding is not None:
        values.update(rounding=rounding)
    gt_value = decimal.Decimal(gt) if isinstance(gt, int) else gt
    gte_value = decimal.Decimal(gte) if isinstance(gte, int) else gte
    lt_value = decimal.Decimal(lt) if isinstance(lt, int) else lt
    lte_value = decimal.Decimal(lte) if isinstance(lte, int) else lte
    if gt_value is not None:
        values.update(gt=gt_value)
    if gt_error is not None:
        values.update(gt_error=gt_error.format(min=gt_value))
    if gte_value is not None:
        values.update(gte=gte_value)
    if gte_error is not None:
        values.update(gte_error=gte_error.format(min=gte_value))
    if lt_value is not None:
        values.update(lt=lt_value)
    if lt_error is not None:
        values.update(lt_error=lt_error.format(max=lt_value))
    if lte_value is not None:
        values.update(lte=lte_value)
    if lte_error is not None:
        values.update(lte_error=lte_error.format(max=lte_value))
    if validate is not None:
        values.update(validate=validate)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def int_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    gt: int | None = None,
    gt_error: str | None = None,
    gte: int | None = None,
    gte_error: str | None = None,
    lt: int | None = None,
    lt_error: str | None = None,
    lte: int | None = None,
    lte_error: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure integer field serialization with range validation.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        gt: Exclusive lower bound (>).
        gt_error: Custom error for gt violation. Supports ``{min}`` placeholder.
        gte: Inclusive lower bound (>=).
        gte_error: Custom error for gte violation. Supports ``{min}`` placeholder.
        lt: Exclusive upper bound (<).
        lt_error: Custom error for lt violation. Supports ``{max}`` placeholder.
        lte: Inclusive upper bound (<=).
        lte_error: Custom error for lte violation. Supports ``{max}`` placeholder.
        validate: Validation function or list of functions applied on load.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    validate_int_bound(gt, "gt")
    validate_int_bound(gte, "gte")
    validate_int_bound(lt, "lt")
    validate_int_bound(lte, "lte")
    if gt is not None and gte is not None:
        raise ValueError("gt and gte are mutually exclusive")
    if lt is not None and lte is not None:
        raise ValueError("lt and lte are mutually exclusive")
    lower = gt if gt is not None else gte
    upper = lt if lt is not None else lte
    if lower is not None and upper is not None:
        if gte is not None and lte is not None:
            if lower > upper:
                raise ValueError(f"lower bound {lower} must be less than or equal to upper bound {upper}")
        elif lower >= upper:
            raise ValueError(f"lower bound {lower} must be less than upper bound {upper}")
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if gt is not None:
        values.update(gt=gt)
    if gt_error is not None:
        values.update(gt_error=gt_error.format(min=gt))
    if gte is not None:
        values.update(gte=gte)
    if gte_error is not None:
        values.update(gte_error=gte_error.format(min=gte))
    if lt is not None:
        values.update(lt=lt)
    if lt_error is not None:
        values.update(lt_error=lt_error.format(max=lt))
    if lte is not None:
        values.update(lte=lte)
    if lte_error is not None:
        values.update(lte_error=lte_error.format(max=lte))
    if validate is not None:
        values.update(validate=validate)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def float_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    gt: float | int | None = None,
    gt_error: str | None = None,
    gte: float | int | None = None,
    gte_error: str | None = None,
    lt: float | int | None = None,
    lt_error: str | None = None,
    lte: float | int | None = None,
    lte_error: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure float field serialization with range validation.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        gt: Exclusive lower bound (>). Accepts float or int.
        gt_error: Custom error for gt violation. Supports ``{min}`` placeholder.
        gte: Inclusive lower bound (>=). Accepts float or int.
        gte_error: Custom error for gte violation. Supports ``{min}`` placeholder.
        lt: Exclusive upper bound (<). Accepts float or int.
        lt_error: Custom error for lt violation. Supports ``{max}`` placeholder.
        lte: Inclusive upper bound (<=). Accepts float or int.
        lte_error: Custom error for lte violation. Supports ``{max}`` placeholder.
        validate: Validation function or list of functions applied on load.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    validate_float_bound(gt, "gt")
    validate_float_bound(gte, "gte")
    validate_float_bound(lt, "lt")
    validate_float_bound(lte, "lte")
    if gt is not None and gte is not None:
        raise ValueError("gt and gte are mutually exclusive")
    if lt is not None and lte is not None:
        raise ValueError("lt and lte are mutually exclusive")
    lower = gt if gt is not None else gte
    upper = lt if lt is not None else lte
    if lower is not None and upper is not None:
        if gte is not None and lte is not None:
            if lower > upper:
                raise ValueError(f"lower bound {lower} must be less than or equal to upper bound {upper}")
        elif lower >= upper:
            raise ValueError(f"lower bound {lower} must be less than upper bound {upper}")
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if gt is not None:
        values.update(gt=gt)
    if gt_error is not None:
        values.update(gt_error=gt_error.format(min=gt))
    if gte is not None:
        values.update(gte=gte)
    if gte_error is not None:
        values.update(gte_error=gte_error.format(min=gte))
    if lt is not None:
        values.update(lt=lt)
    if lt_error is not None:
        values.update(lt_error=lt_error.format(max=lt))
    if lte is not None:
        values.update(lte=lte)
    if lte_error is not None:
        values.update(lte_error=lte_error.format(max=lte))
    if validate is not None:
        values.update(validate=validate)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def datetime_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    format: str | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure datetime field serialization with custom format.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        validate: Validation function or list of functions applied on load.
        format: strftime/strptime format string for serialization.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    validate_datetime_format(format)
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if validate is not None:
        values.update(validate=validate)
    if format is not None:
        values.update(format=format)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def time_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure time field serialization.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        validate: Validation function or list of functions applied on load.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if validate is not None:
        values.update(validate=validate)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def list_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    item_description: str | None = None,
    min_length: int | None = None,
    min_length_error: str | None = None,
    max_length: int | None = None,
    max_length_error: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure list field serialization with item and length validation.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        item_description: Description for list items, used in JSON Schema.
        min_length: Minimum number of items in the list.
        min_length_error: Custom error for min_length violation. Supports ``{min}`` placeholder.
        max_length: Maximum number of items in the list.
        max_length_error: Custom error for max_length violation. Supports ``{max}`` placeholder.
        validate: Validation function or list of functions for the list itself.
        validate_item: Validation function or list of functions applied to each item.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    validate_length_bound(min_length, "min_length")
    validate_length_bound(max_length, "max_length")
    if min_length is not None and max_length is not None and min_length > max_length:
        raise ValueError(f"min_length {min_length} must be less than or equal to max_length {max_length}")
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if item_description is not None:
        values.update(item_description=item_description)
    if min_length is not None:
        values.update(min_length=min_length)
    if min_length_error is not None:
        values.update(min_length_error=min_length_error.format(min=min_length))
    if max_length is not None:
        values.update(max_length=max_length)
    if max_length_error is not None:
        values.update(max_length_error=max_length_error.format(max=max_length))
    if validate is not None:
        values.update(validate=validate)
    if validate_item is not None:
        values.update(validate_item=validate_item)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def set_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    item_description: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure set field serialization with item validation.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        item_description: Description for set items, used in JSON Schema.
        validate: Validation function or list of functions for the set itself.
        validate_item: Validation function or list of functions applied to each item.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if item_description is not None:
        values.update(item_description=item_description)
    if validate is not None:
        values.update(validate=validate)
    if validate_item is not None:
        values.update(validate_item=validate_item)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def tuple_metadata(
    *,
    name: str = MISSING,
    description: str | None = None,
    item_description: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    """Configure tuple field serialization with item validation.

    Args:
        name: Override serialized field name.
        description: Field description, used in JSON Schema generation.
        item_description: Description for tuple items, used in JSON Schema.
        validate: Validation function or list of functions for the tuple itself.
        validate_item: Validation function or list of functions applied to each item.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
    """
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if item_description is not None:
        values.update(item_description=item_description)
    if validate is not None:
        values.update(validate=validate)
    if validate_item is not None:
        values.update(validate_item=validate_item)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    return Metadata(values)


def frozenset_metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
) -> Metadata:
    """Configure frozenset field serialization with item validation.

    Args:
        name: Override serialized field name.
        validate: Validation function or list of functions for the frozenset itself.
        validate_item: Validation function or list of functions applied to each item.
        required_error: Custom error message when required field is missing.
        none_error: Custom error message when field is None but shouldn't be.
        invalid_error: Custom error message when field value has invalid type.
        description: Field description, used in JSON Schema generation.
    """
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    if validate_item is not None:
        values.update(validate_item=validate_item)
    if required_error is not None:
        values.update(required_error=required_error)
    if none_error is not None:
        values.update(none_error=none_error)
    if invalid_error is not None:
        values.update(invalid_error=invalid_error)
    if description is not None:
        values.update(description=description)
    return Metadata(values)


sequence_metadata = list_metadata

# shortcuts
meta = metadata
decimal_meta = decimal_metadata
datetime_meta = datetime_metadata
list_meta = list_metadata
set_meta = set_metadata
frozenset_meta = frozenset_metadata
sequence_meta = sequence_metadata
str_meta = str_metadata
tuple_meta = tuple_metadata
int_meta = int_metadata
float_meta = float_metadata
