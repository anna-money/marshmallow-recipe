from typing import Any, Callable, Mapping

from .missing import MISSING


def metadata(
    *,
    name: str = MISSING,
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
    name: str = MISSING,
    places: int = MISSING,
    as_string: bool = MISSING,
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
