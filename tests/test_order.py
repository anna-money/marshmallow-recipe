import dataclasses

import marshmallow_recipe as mr


def test_order_1() -> None:
    @dataclasses.dataclass
    class A:
        a: int
        b: int

    assert list(mr.dump(A(a=1, b=2))) == ["a", "b"]


def test_order_2() -> None:
    @dataclasses.dataclass
    class A:
        b: int
        a: int

    assert list(mr.dump(A(b=1, a=2))) == ["b", "a"]
