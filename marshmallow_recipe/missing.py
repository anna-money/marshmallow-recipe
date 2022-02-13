from typing import NewType

MissingType = NewType("MissingType", object)

MISSING = MissingType(object())
