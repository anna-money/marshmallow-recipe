from .missing import MISSING


def validate_decimal_places(value: int | None) -> None:
    if value is MISSING or value is None or value >= 0:
        return
    raise ValueError(f"decimal_places must be None or a non-negative integer, got {value!r}")
