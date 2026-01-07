from collections.abc import Callable
from typing import Any

import marshmallow


def build_combined_validator(validators: list[Callable]) -> Callable[[Any], list[Any] | None]:
    """Combine validators into a single function returning list of errors or None."""

    def combined(value: Any) -> list[Any] | None:
        errors: list[Any] | None = None
        for validator in validators:
            try:
                result = validator(value)
                if result is False:
                    if errors is None:
                        errors = []
                    errors.append("Invalid value.")
            except marshmallow.ValidationError as e:
                if errors is None:
                    errors = []
                if isinstance(e.messages, list):
                    errors.extend(e.messages)
                else:
                    errors.append(e.messages)
            except Exception:
                if errors is None:
                    errors = []
                errors.append("Invalid value.")
        return errors

    return combined
