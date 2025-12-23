import functools
import typing

import marshmallow

from marshmallow_recipe.v2 import _core  # type: ignore[attr-defined]
from marshmallow_recipe.v2._descriptor import TypeDescriptor, build_type_descriptor

__all__ = ["dump", "load"]


def _convert_rust_error_to_validation_error(e: ValueError) -> marshmallow.ValidationError:
    if hasattr(e, "args") and len(e.args) > 0 and isinstance(e.args[0], dict):
        return marshmallow.ValidationError(e.args[0])
    raise e


@functools.lru_cache(maxsize=128)
def _get_cached_descriptor(cls: typing.Any, naming_case: typing.Callable[[str], str] | None) -> TypeDescriptor:
    return build_type_descriptor(cls, naming_case)


def dump[T](
    cls: type[T],
    data: T,
    *,
    naming_case: typing.Callable[[str], str] | None = None,
    none_value_handling: str | None = None,
) -> bytes:
    descriptor = _get_cached_descriptor(cls, naming_case)
    none_handling = none_value_handling if none_value_handling else "ignore"
    return _core.dump_to_json(data, descriptor, none_handling)


def load[T](cls: type[T], data: bytes, *, naming_case: typing.Callable[[str], str] | None = None) -> T:
    descriptor = _get_cached_descriptor(cls, naming_case)
    try:
        return _core.load_from_json(data, descriptor)  # type: ignore[return-value]
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)
