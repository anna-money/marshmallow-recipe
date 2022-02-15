from typing import NewType

Missing = NewType("Missing", object)

MISSING = Missing(object())
