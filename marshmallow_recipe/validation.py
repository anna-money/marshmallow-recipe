import collections.abc
import dataclasses
import re
from typing import Any

import marshmallow.validate

ValidationFunc = collections.abc.Callable[[Any], Any]


def regexp_validate(regexp: re.Pattern | str, *, error: str | None = None) -> ValidationFunc:
    return marshmallow.validate.Regexp(regexp, error=error)


def validate(validator: ValidationFunc, *, error: str | None = None) -> ValidationFunc:
    if error is None:
        return validator

    def _validator_with_custom_error(value: Any) -> Any:
        result = validator(value)
        if result is False:
            raise marshmallow.ValidationError(error)
        return result

    return _validator_with_custom_error


ValidationError = marshmallow.ValidationError


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class ValidationFieldError:
    name: str
    error: str | None = None
    nested_errors: list["ValidationFieldError"] | None = None


def get_field_errors(exc: ValidationError) -> list[ValidationFieldError]:
    return __get_field_errors_from_normalized_messages(exc.normalized_messages())


def __get_field_errors_from_normalized_messages(normalized_messages: dict[Any, Any]) -> list[ValidationFieldError]:
    errors: list["ValidationFieldError"] = []

    for key, value in normalized_messages.items():
        if not isinstance(key, (str, int)):
            continue

        if isinstance(value, dict):
            errors.append(
                ValidationFieldError(name=str(key), nested_errors=__get_field_errors_from_normalized_messages(value))
            )
        elif isinstance(value, str):
            errors.append(ValidationFieldError(name=str(key), error=value))
        elif isinstance(value, list) and all([isinstance(item, str) for item in value]):
            errors.append(ValidationFieldError(name=str(key), error=str.join("; ", value)))

    errors.sort(key=lambda x: x.name)

    return errors
