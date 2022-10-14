import inspect
from typing import Any, Callable, Type

_PRE_LOAD = "__marshmallow_recipe_pre_load_"
_PRE_LOAD_CLASS_ = "__marshmallow_recipe_pre_load_class_"


def pre_load(fn: Callable[..., Any]) -> Callable[..., Any]:
    setattr(fn, _PRE_LOAD, True)
    return fn


def get_pre_loads(cls: Type) -> list[Callable[..., Any]]:
    result = []
    for _, method in inspect.getmembers(cls):
        if hasattr(method, _PRE_LOAD):
            result.append(method)
    for fn in getattr(cls, _PRE_LOAD_CLASS_, []):
        result.append(fn)
    return result


def add_pre_load(cls: Type, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    if not hasattr(cls, _PRE_LOAD_CLASS_):
        setattr(cls, _PRE_LOAD_CLASS_, [])
    pre_loads: list = getattr(cls, _PRE_LOAD_CLASS_)
    pre_loads.append(fn)
