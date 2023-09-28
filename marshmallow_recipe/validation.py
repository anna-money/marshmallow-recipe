import collections.abc
import re
from typing import Any

import marshmallow.validate

ValidationFunc = collections.abc.Callable[[Any], Any]


def regexp_validate(regexp: re.Pattern | str, *, error: str | None) -> ValidationFunc:
    return marshmallow.validate.Regexp(regexp, error=error)
