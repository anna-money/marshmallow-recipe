import collections.abc
from typing import Any, TypeGuard, final

from .missing import MISSING
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


def metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    return Metadata(values)


def str_metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    strip_whitespaces: bool | None = None,
    post_load: collections.abc.Callable[[str], str] | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    if strip_whitespaces is not None:
        values.update(strip_whitespaces=strip_whitespaces)
    if post_load is not None:
        values.update(post_load=post_load)
    return Metadata(values)


def decimal_metadata(
    *,
    name: str = MISSING,
    places: int | None = MISSING,
    as_string: bool = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if places is not MISSING:
        values.update(places=places)
    if as_string is not MISSING:
        values.update(as_string=as_string)
    if validate is not None:
        values.update(validate=validate)
    return Metadata(values)


def datetime_metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    format: str | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    if format is not None:
        values.update(format=format)
    return Metadata(values)


def time_metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    return Metadata(values)


def list_metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    if validate_item is not None:
        values.update(validate_item=validate_item)
    return Metadata(values)


def set_metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    if validate_item is not None:
        values.update(validate_item=validate_item)
    return Metadata(values)


def tuple_metadata(
    *,
    name: str = MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    validate_item: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
) -> Metadata:
    values = dict[str, Any]()
    if name is not MISSING:
        values.update(name=name)
    if validate is not None:
        values.update(validate=validate)
    if validate_item is not None:
        values.update(validate_item=validate_item)
    return Metadata(values)


sequence_metadata = list_metadata

# shortcuts
meta = metadata
decimal_meta = decimal_metadata
datetime_meta = datetime_metadata
list_meta = list_metadata
set_meta = set_metadata
sequence_meta = sequence_metadata
str_meta = str_metadata
tuple_meta = tuple_metadata
