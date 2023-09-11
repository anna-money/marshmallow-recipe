import collections.abc
import inspect
from typing import Any, Type

_PRE_LOAD_KEY = "__marshmallow_recipe_pre_load__"
_PRE_LOAD_CLASS_KEY = "__marshmallow_recipe_pre_load_class__"


def pre_load(fn: collections.abc.Callable[..., Any]) -> collections.abc.Callable[..., Any]:
    setattr(fn, _PRE_LOAD_KEY, True)
    return fn


def get_pre_loads(cls: Type) -> list[collections.abc.Callable[..., Any]]:
    result = []
    for _, method in inspect.getmembers(cls):
        if hasattr(method, _PRE_LOAD_KEY):
            result.append(method)
    for fn in getattr(cls, _PRE_LOAD_CLASS_KEY, []):
        result.append(fn)
    return result


def add_pre_load(cls: Type, fn: collections.abc.Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    if not hasattr(cls, _PRE_LOAD_CLASS_KEY):
        setattr(cls, _PRE_LOAD_CLASS_KEY, [])
    pre_loads: list = getattr(cls, _PRE_LOAD_CLASS_KEY)
    pre_loads.append(fn)
