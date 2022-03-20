from typing import Any, Callable, Mapping

from .missing import MISSING, Missing


def metadata(
    *,
    name: str | Missing = MISSING,
    validate: Callable[[Any], Any] | None = None,
) -> Mapping[Any, Any]:
    result: dict[Any, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if validate is not None:
        result.update(validate=validate)
    return result


def decimal_metadata(
    *,
    name: str | Missing = MISSING,
    places: int | Missing = MISSING,
    as_string: bool | Missing = MISSING,
    validate: Callable[[Any], Any] | None = None,
) -> Mapping[Any, Any]:
    result: dict[Any, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if places is not MISSING:
        result.update(places=places)
    if as_string is not MISSING:
        result.update(as_string=as_string)
    if validate is not None:
        result.update(validate=validate)
    return result
