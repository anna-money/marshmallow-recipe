import collections.abc
import inspect
from typing import Any

_PRE_LOAD_KEY = "__marshmallow_recipe_pre_load__"
_PRE_LOAD_CLASS_KEY = "__marshmallow_recipe_pre_load_class__"
_PRE_LOADS_CACHE = {}


def pre_load(fn: collections.abc.Callable[..., Any]) -> collections.abc.Callable[..., Any]:
    setattr(fn, _PRE_LOAD_KEY, True)
    return fn


def get_pre_loads(cls: type) -> list[collections.abc.Callable[..., Any]]:
    existing = _PRE_LOADS_CACHE.get(cls)
    if existing is not None:
        return existing

    result = []
    for _, method in inspect.getmembers(cls):
        if hasattr(method, _PRE_LOAD_KEY):
            result.append(method)
    for fn in getattr(cls, _PRE_LOAD_CLASS_KEY, []):
        result.append(fn)
    _PRE_LOADS_CACHE[cls] = result
    return result


def add_pre_load(cls: type, fn: collections.abc.Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    if not hasattr(cls, _PRE_LOAD_CLASS_KEY):
        setattr(cls, _PRE_LOAD_CLASS_KEY, [])
    pre_loads: list = getattr(cls, _PRE_LOAD_CLASS_KEY)
    pre_loads.append(fn)
