import collections.abc
import dataclasses
import re
from typing import Any

import marshmallow
import marshmallow.validate

ValidationFunc = collections.abc.Callable[[Any], Any]


def combine_validators(
    this: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None, that: ValidationFunc
) -> ValidationFunc | collections.abc.Sequence[ValidationFunc]:
    if this is None:
        return that
    if callable(this):
        return [this, that]
    return [*this, that]


def __wrap_validator(validator: ValidationFunc) -> ValidationFunc:
    def _wrapper(value: Any) -> None:
        if validator(value) is False:
            raise marshmallow.ValidationError("Invalid value.")

    return _wrapper


def wrap_validators(
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None,
) -> ValidationFunc | list[ValidationFunc] | None:
    if validate is None:
        return None
    if isinstance(validate, collections.abc.Sequence) and not callable(validate):
        return [__wrap_validator(v) for v in validate]
    return __wrap_validator(validate)


def regexp_validate(regexp: re.Pattern | str, *, error: str | None = None) -> ValidationFunc:
    return marshmallow.validate.Regexp(regexp, error=error)


def email_validate(*, error: str | None = None) -> ValidationFunc:
    class Email(marshmallow.validate.Email):
        # RESTRICT QUOTED STRINGS: Prohibiting double-quotes (") in the local-part
        # (the part before the @) ensures compatibility with most major email systems,
        # as the full RFC-valid quoted format is rarely supported in practice.
        USER_REGEX = re.compile(r"(^[-!#$%&'*+/=?^`{}|~\w]+(\.[-!#$%&'*+/=?^`{}|~\w]+)*$)", re.IGNORECASE | re.UNICODE)

    return Email(error=error)


def validate(validator: ValidationFunc, *, error: str | None = None) -> ValidationFunc:
    if error is None:
        return __wrap_validator(validator)

    def _validator_with_custom_error(value: Any) -> None:
        if validator(value) is False:
            raise marshmallow.ValidationError(error)

    return _validator_with_custom_error


ValidationError = marshmallow.ValidationError


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ValidationFieldError:
    name: str
    error: str | None = None
    nested_errors: list["ValidationFieldError"] | None = None


def get_validation_field_errors(exc: ValidationError) -> list[ValidationFieldError]:
    return __get_field_errors_from_normalized_messages(exc.normalized_messages())


def __get_field_errors_from_normalized_messages(normalized_messages: dict[Any, Any]) -> list[ValidationFieldError]:
    field_errors: list[ValidationFieldError] = []

    for key, value in normalized_messages.items():
        if not isinstance(key, str | int):
            continue

        name = str(key)
        error: str | None = None
        nested_errors: list[ValidationFieldError] | None = None

        if isinstance(value, dict):
            nested_errors = __get_field_errors_from_normalized_messages(value)
        elif isinstance(value, str):
            error = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            error = "; ".join(value)
        else:
            continue

        field_errors.append(ValidationFieldError(name=name, error=error, nested_errors=nested_errors))

    field_errors.sort(key=lambda x: x.name)

    return field_errors
