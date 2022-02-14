from typing import Any, Mapping

from .missing import MISSING, Missing


def metadata(
    *,
    name: str | Missing = MISSING,
) -> Mapping[Any, Any]:
    result: dict[Any, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    return result


def decimal_metadata(
    *,
    name: str | Missing = MISSING,
    places: int | Missing = MISSING,
    as_string: bool | Missing = MISSING,
) -> Mapping[Any, Any]:
    result: dict[Any, Any] = {}
    if name is not MISSING:
        result.update(name=name)
    if places is not MISSING:
        result.update(places=places)
    if as_string is not MISSING:
        result.update(as_string=as_string)
    return result
