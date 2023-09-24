import collections.abc
from typing import Any

import marshmallow as m

ValidationFunc = collections.abc.Callable[[Any], Any]


class ValidationError(m.ValidationError):
    def __init__(self, message: str):
        super().__init__(message)
