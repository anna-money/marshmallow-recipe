import collections.abc
from typing import Any

from .missing import MISSING


def metadata(
    *,
    name: str = MISSING,
    validate: collections.abc.Callable[[Any], Any] | None = None,
) -> collections.abc.Mapping[str, Any]:
    result: dict[str, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if validate is not None:
        result.update(validate=validate)
    return result


def decimal_metadata(
    *,
    name: str = MISSING,
    places: int = MISSING,
    as_string: bool = MISSING,
    validate: collections.abc.Callable[[Any], Any] | None = None,
) -> collections.abc.Mapping[str, Any]:
    result: dict[str, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if places is not MISSING:
        result.update(places=places)
    if as_string is not MISSING:
        result.update(as_string=as_string)
    if validate is not None:
        result.update(validate=validate)
    return result


def datetime_metadata(
    *,
    name: str = MISSING,
    validate: collections.abc.Callable[[Any], Any] | None = None,
    format: str | None = None,
) -> collections.abc.Mapping[str, Any]:
    result: dict[str, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if validate is not None:
        result.update(validate=validate)
    if format is not None:
        result.update(format=format)
    return result


def list_metadata(
    *,
    name: str = MISSING,
    validate: collections.abc.Callable[[Any], Any] | None = None,
    validate_item: collections.abc.Callable[[Any], Any] | None = None,
) -> collections.abc.Mapping[str, Any]:
    result: dict[str, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if validate is not None:
        result.update(validate=validate)
    if validate_item is not None:
        result.update(validate_item=validate_item)
    return result


sequence_metadata = list_metadata


def set_metadata(
    *,
    name: str = MISSING,
    validate: collections.abc.Callable[[Any], Any] | None = None,
    validate_item: collections.abc.Callable[[Any], Any] | None = None,
) -> collections.abc.Mapping[str, Any]:
    result: dict[str, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if validate is not None:
        result.update(validate=validate)
    if validate_item is not None:
        result.update(validate_item=validate_item)
    return result


def tuple_metadata(
    *,
    name: str = MISSING,
    validate: collections.abc.Callable[[Any], Any] | None = None,
    validate_item: collections.abc.Callable[[Any], Any] | None = None,
) -> collections.abc.Mapping[str, Any]:
    result: dict[str, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if validate is not None:
        result.update(validate=validate)
    if validate_item is not None:
        result.update(validate_item=validate_item)
    return result
