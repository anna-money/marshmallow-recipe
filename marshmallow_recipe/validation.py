import collections.abc
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
