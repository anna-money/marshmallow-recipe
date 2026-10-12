# pyright: reportUnnecessaryTypeIgnoreComment=true
import dataclasses
from typing import Any, assert_type

import pytest

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: int
    name: str


def test_dump_without_cls_returns_dict() -> None:
    result = mr.nuked.dump(User(id=1, name="John"))
    assert_type(result, dict[str, Any])
    assert result == {"id": 1, "name": "John"}


def test_dump_without_cls_rejects_non_dataclass_statically() -> None:
    with pytest.raises(ValueError):
        mr.nuked.dump(42)  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.nuked.dump([User(id=1, name="John")])  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.nuked.dump(None)  # type: ignore[call-overload]
