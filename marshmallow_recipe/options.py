import dataclasses
import enum
from typing import Any

from .naming_case import DEFAULT_CASE, NamingCase

_OPTIONS = "__marshmallow_recipe_options_"


class NoneValueHandling(str, enum.Enum):
    IGNORE = "IGNORE"
    INCLUDE = "INCLUDE"

    def __str__(self) -> str:
        return self.value


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DataclassOptions:
    none_value_handling: NoneValueHandling
    naming_case: NamingCase


_DEFAULT_OPTIONS = DataclassOptions(
    none_value_handling=NoneValueHandling.IGNORE,
    naming_case=DEFAULT_CASE,
)


def options(
    *,
    none_value_handling: NoneValueHandling = _DEFAULT_OPTIONS.none_value_handling,
    naming_case: NamingCase = _DEFAULT_OPTIONS.naming_case,
):
    def wrap(cls: Any):
        setattr(
            cls,
            _OPTIONS,
            DataclassOptions(
                none_value_handling=none_value_handling,
                naming_case=naming_case,
            ),
        )
        return cls

    return wrap


def get_options_for(type) -> DataclassOptions:
    return getattr(type, _OPTIONS, _DEFAULT_OPTIONS)
