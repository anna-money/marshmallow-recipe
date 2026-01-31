import json
import typing
from collections.abc import Callable

import marshmallow

from .. import _nuked as nuked  # type: ignore[attr-defined]
from ..hooks import get_pre_loads
from ..options import NoneValueHandling
from ..utils import validate_decimal_places
from ._descriptor import TypeDescriptor, build_type_descriptor
from ._schema import descriptor_to_dict

__all__ = ("dump", "dump_to_bytes", "load", "load_from_bytes")

_schema_id_counter: int = 0
_schema_id_map: dict[tuple[type, Callable[[str], str] | None], int] = {}
_schema_cache: dict[int, TypeDescriptor] = {}


def _get_schema_id(cls: type, naming_case: Callable[[str], str] | None) -> int:
    global _schema_id_counter
    key = (cls, naming_case)
    if key not in _schema_id_map:
        _schema_id_map[key] = _schema_id_counter
        _schema_id_counter += 1
    return _schema_id_map[key]


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


def _ensure_registered(cls: type, naming_case: Callable[[str], str] | None) -> int:
    schema_id = _get_schema_id(cls, naming_case)

    if schema_id not in _schema_cache:
        descriptor = build_type_descriptor(cls, naming_case)
        raw_schema = descriptor_to_dict(descriptor)
        _schema_cache[schema_id] = descriptor
        nuked.register(schema_id, raw_schema)

    return schema_id


def dump_to_bytes[T](
    cls: type[T],
    data: T,
    *,
    naming_case: typing.Callable[[str], str] | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = None,
    encoding: str = "utf-8",
) -> bytes:
    validate_decimal_places(decimal_places)
    schema_id = _ensure_registered(cls, naming_case)
    descriptor = _schema_cache[schema_id]

    effective_none_handling = none_value_handling or descriptor.none_value_handling or NoneValueHandling.IGNORE

    try:
        return nuked.dump_to_bytes(schema_id, data, effective_none_handling.value, decimal_places, encoding)
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)


def load_from_bytes[T](
    cls: type[T],
    data: bytes,
    *,
    naming_case: typing.Callable[[str], str] | None = None,
    decimal_places: int | None = None,
    encoding: str = "utf-8",
) -> T:
    validate_decimal_places(decimal_places)
    schema_id = _ensure_registered(cls, naming_case)
    try:
        return nuked.load_from_bytes(schema_id, data, decimal_places, encoding)  # type: ignore[return-value]
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)


def dump[T](
    cls: type[T],
    data: T,
    *,
    naming_case: typing.Callable[[str], str] | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = None,
) -> typing.Any:
    validate_decimal_places(decimal_places)
    schema_id = _ensure_registered(cls, naming_case)
    descriptor = _schema_cache[schema_id]

    effective_none_handling = none_value_handling or descriptor.none_value_handling or NoneValueHandling.IGNORE

    try:
        return nuked.dump(schema_id, data, effective_none_handling.value, decimal_places)
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
    schema_id = _ensure_registered(cls, naming_case)

    for pre_load in get_pre_loads(cls):
        data = pre_load(data)

    try:
        return nuked.load(schema_id, data, decimal_places)  # type: ignore[return-value]
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)
