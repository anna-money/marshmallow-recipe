import collections.abc
import dataclasses
import enum
from typing import TypeVar

from .naming_case import NamingCase

_OPTIONS_KEY = "__marshmallow_recipe_options__"


class NoneValueHandling(enum.StrEnum):
    IGNORE = enum.auto()
    INCLUDE = enum.auto()


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DataclassOptions:
    none_value_handling: NoneValueHandling | None = None
    naming_case: NamingCase | None = None


_T = TypeVar("_T")


def options(
    *,
    none_value_handling: NoneValueHandling | None = None,
    naming_case: NamingCase | None = None,
) -> collections.abc.Callable[[type[_T]], type[_T]]:
    def wrap(cls: type[_T]) -> type[_T]:
        setattr(
            cls,
            _OPTIONS_KEY,
            DataclassOptions(
                none_value_handling=none_value_handling,
                naming_case=naming_case,
            ),
        )
        return cls

    return wrap


def try_get_options_for(type: type) -> DataclassOptions | None:
    return getattr(type, _OPTIONS_KEY, None)
