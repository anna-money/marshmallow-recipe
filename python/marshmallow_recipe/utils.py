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


def validate_decimal_bound(value: decimal.Decimal | int | None, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        raise TypeError(f"{name} must be Decimal or int, got bool")
    if not isinstance(value, decimal.Decimal | int):  # type: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"{name} must be Decimal or int, got {type(value).__name__}")


def validate_str_length(value: int | None, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        raise TypeError(f"{name} must be int, got bool")
    if not isinstance(value, int):  # type: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"{name} must be int, got {type(value).__name__}")


def validate_str_regexp(value: str | None) -> None:
    if value is None:
        return
    if not isinstance(value, str):  # type: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"regexp must be str, got {type(value).__name__}")


def validate_int_bound(value: int | None, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        raise TypeError(f"{name} must be int, got bool")
    if not isinstance(value, int):  # type: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"{name} must be int, got {type(value).__name__}")


def validate_float_bound(value: float | int | None, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        raise TypeError(f"{name} must be float or int, got bool")
    if isinstance(value, float):
        import math

        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"{name} must be a finite number, got {value!r}")
        return
    if not isinstance(value, int):  # type: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"{name} must be float or int, got {type(value).__name__}")


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
