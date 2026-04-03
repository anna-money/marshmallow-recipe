import collections.abc
import dataclasses
import enum

from .missing import MISSING
from .naming_case import NamingCase
from .utils import validate_decimal_places

_OPTIONS_KEY = "__marshmallow_recipe_options__"


class NoneValueHandling(enum.StrEnum):
    IGNORE = enum.auto()
    INCLUDE = enum.auto()


@dataclasses.dataclass(kw_only=True, slots=True, frozen=True)
class DataclassOptions:
    none_value_handling: NoneValueHandling | None = None
    naming_case: NamingCase | None = None
    decimal_places: int | None = MISSING
    title: str | None = None
    description: str | None = None


def options[T](
    *,
    none_value_handling: NoneValueHandling | None = None,
    naming_case: NamingCase | None = None,
    decimal_places: int | None = MISSING,
    title: str | None = None,
    description: str | None = None,
) -> collections.abc.Callable[[type[T]], type[T]]:
    """Decorator to set dataclass-level serialization settings.

    Nested dataclasses keep their own @mr.options — NOT inherited from parent.
    Settings can be overridden per call: ``mr.dump(obj, naming_case=mr.CAMEL_CASE)``.

    Args:
        none_value_handling: Controls None field output.
            ``mr.NoneValueHandling.INCLUDE`` keeps None fields, default excludes them.
        naming_case: Convert field names. Use ``mr.CAMEL_CASE``,
            ``mr.CAPITAL_CAMEL_CASE``, or ``mr.UPPER_SNAKE_CASE``.
        decimal_places: Validate maximum decimal places for all Decimal fields.
        title: Schema title, used in JSON Schema generation.
        description: Schema description, used in JSON Schema generation.
    """
    validate_decimal_places(decimal_places)

    def wrap(cls: type[T]) -> type[T]:
        setattr(
            cls,
            _OPTIONS_KEY,
            DataclassOptions(
                none_value_handling=none_value_handling,
                naming_case=naming_case,
                decimal_places=decimal_places,
                title=title,
                description=description,
            ),
        )
        return cls

    return wrap


def try_get_options_for(type: type) -> DataclassOptions | None:
    return getattr(type, _OPTIONS_KEY, None)
