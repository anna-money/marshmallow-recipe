# pyright: reportUnnecessaryTypeIgnoreComment=true
import dataclasses
from typing import Any, assert_type

import pytest

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: int
    name: str


def test_dump_return_types() -> None:
    user = User(id=1, name="John")
    expected = {"id": 1, "name": "John"}
    assert assert_type(mr.dump(user), dict[str, Any]) == expected
    assert assert_type(mr.dump(User, user), dict[str, Any]) == expected
    assert assert_type(mr.nuked.dump(user), dict[str, Any]) == expected
    assert assert_type(mr.nuked.dump(User, user), dict[str, Any]) == expected
    assert assert_type(mr.nuked.dump(list[User], [user]), Any) == [expected]


def test_dump_without_cls_rejects_non_dataclass_statically() -> None:
    with pytest.raises(ValueError):
        mr.dump(42)  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.dump([User(id=1, name="John")])  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.dump(None)  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.dump(User)  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.nuked.dump(42)  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.nuked.dump([User(id=1, name="John")])  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.nuked.dump(None)  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        mr.nuked.dump(User)  # type: ignore[call-overload]
