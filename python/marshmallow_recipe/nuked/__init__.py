import dataclasses
import json
import typing
from collections.abc import Callable

import marshmallow

from ..hooks import get_pre_loads
from ..options import NoneValueHandling
from ..utils import validate_decimal_places
from ._container import build_container, get_dataclass_info

__all__ = ("dump", "load")


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _ContainerKey:
    cls: type
    naming_case: Callable[[str], str] | None
    none_value_handling: NoneValueHandling
    decimal_places: int | None


_container_cache: dict[_ContainerKey, typing.Any] = {}


def _convert_rust_error_to_validation_error(e: ValueError) -> marshmallow.ValidationError:
    if hasattr(e, "args") and len(e.args) > 0:
        msg = e.args[0]
        if isinstance(msg, dict | list):
            return marshmallow.ValidationError(msg)
        if isinstance(msg, str):
            try:
                return marshmallow.ValidationError(json.loads(msg))
            except json.JSONDecodeError:
                pass
    raise e


def _get_container(
    cls: type,
    naming_case: Callable[[str], str] | None,
    none_value_handling: NoneValueHandling,
    decimal_places: int | None,
) -> typing.Any:
    key = _ContainerKey(
        cls=cls, naming_case=naming_case, none_value_handling=none_value_handling, decimal_places=decimal_places
    )

    if key not in _container_cache:
        container = build_container(cls, naming_case, none_value_handling, decimal_places)
        _container_cache[key] = container

    return _container_cache[key]


def dump[T](
    cls: type[T],
    data: T,
    *,
    naming_case: typing.Callable[[str], str] | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = None,
) -> typing.Any:
    validate_decimal_places(decimal_places)
    info = get_dataclass_info(cls, naming_case)
    effective_none_handling = (
        none_value_handling or (info.none_value_handling if info else None) or NoneValueHandling.IGNORE
    )
    effective_decimal_places = decimal_places if decimal_places is not None else (info.decimal_places if info else None)

    container = _get_container(cls, naming_case, effective_none_handling, effective_decimal_places)

    try:
        return container.dump(data)
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)


def load[T](
    cls: type[T],
    data: typing.Any,
    *,
    naming_case: typing.Callable[[str], str] | None = None,
    decimal_places: int | None = None,
) -> T:
    validate_decimal_places(decimal_places)
    info = get_dataclass_info(cls, naming_case)
    effective_decimal_places = decimal_places if decimal_places is not None else (info.decimal_places if info else None)

    container = _get_container(cls, naming_case, NoneValueHandling.IGNORE, effective_decimal_places)

    if info is not None:
        for pre_load in get_pre_loads(info.cls):
            data = pre_load(data)

    try:
        return container.load(data)  # type: ignore[return-value]
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)
