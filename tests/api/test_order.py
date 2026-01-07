import dataclasses

from .conftest import Serializer


class TestFieldOrderDump:
    def test_a_b(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class A:
            a: int
            b: int

        obj = A(a=1, b=2)
        result = impl.dump(A, obj)
        assert result == b'{"a":1,"b":2}'

    def test_b_a(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class A:
            b: int
            a: int

        obj = A(b=1, a=2)
        result = impl.dump(A, obj)
        assert result == b'{"b":1,"a":2}'
