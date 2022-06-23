import dataclasses
import enum
from typing import Any

_OPTIONS = "__marshmallow_recipe_options_"


class NoneValueHandling(str, enum.Enum):
    IGNORE = "IGNORE"
    INCLUDE = "INCLUDE"

    def __str__(self) -> str:
        return self.value


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class MarshmallowRecipeOptions:
    none_value_handling: NoneValueHandling


_DEFAULT_OPTIONS = MarshmallowRecipeOptions(
    none_value_handling=NoneValueHandling.IGNORE,
)


def options(*, none_value_handling: NoneValueHandling = _DEFAULT_OPTIONS.none_value_handling):
    def wrap(cls: Any):
        setattr(
            cls,
            _OPTIONS,
            MarshmallowRecipeOptions(
                none_value_handling=none_value_handling,
            ),
        )
        return cls

    return wrap


def get_options_for(type) -> MarshmallowRecipeOptions:
    if not hasattr(type, _OPTIONS):
        return _DEFAULT_OPTIONS
    return getattr(type, _OPTIONS)
