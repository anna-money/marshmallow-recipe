import collections.abc
from typing import Any, TypeGuard, final

from .missing import MISSING
from .utils import validate_datetime_format, validate_decimal_places, validate_decimal_rounding
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
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    strip_whitespaces: bool | None = None,
    post_load: collections.abc.Callable[[str], str] | None = None,
    min_length: int | None = None,
    min_length_error: str | None = None,
    max_length: int | None = None,
    max_length_error: str | None = None,
    regexp: str | None = None,
    regexp_error: str | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if validate is not None:
        values.update(validate=validate)
    if strip_whitespaces is not None:
        values.update(strip_whitespaces=strip_whitespaces)
    if post_load is not None:
        values.update(post_load=post_load)
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
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
    validate_decimal_places(places)
    validate_decimal_rounding(rounding)
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if description is not None:
        values.update(description=description)
    if places is not MISSING:
        values.update(places=places)
    if rounding is not None:
        values.update(rounding=rounding)
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
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
) -> Metadata:
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
