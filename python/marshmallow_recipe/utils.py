import decimal

from .missing import MISSING

SUPPORTED_DECIMAL_ROUNDING_MODES: frozenset[str] = frozenset(
    {
        decimal.ROUND_UP,
        decimal.ROUND_DOWN,
        decimal.ROUND_CEILING,
        decimal.ROUND_FLOOR,
        decimal.ROUND_HALF_UP,
        decimal.ROUND_HALF_DOWN,
        decimal.ROUND_HALF_EVEN,
    }
)


def validate_decimal_places(value: int | None) -> None:
    if value is MISSING or value is None or value >= 0:
        return
    raise ValueError(f"decimal_places must be None or a non-negative integer, got {value!r}")


def validate_decimal_rounding(value: str | None) -> None:
    if value is None:
        return
    if value not in SUPPORTED_DECIMAL_ROUNDING_MODES:
        raise ValueError(
            f"Unsupported rounding mode: {value!r}. "
            f"Supported modes: {', '.join(sorted(SUPPORTED_DECIMAL_ROUNDING_MODES))}"
        )


SUPPORTED_DATETIME_FORMATS: frozenset[str] = frozenset({"iso", "timestamp"})


def validate_datetime_format(value: str | None) -> None:
    if value is None:
        return
    if value in SUPPORTED_DATETIME_FORMATS:
        return
    if "%" not in value:
        raise ValueError(
            f"Invalid datetime format: {value!r}. " f"Use 'iso', 'timestamp', or a strftime pattern containing '%'"
        )
