"""Union member order must survive the container cache.

``A | B`` and ``B | A`` are equal Python objects with equal hashes, but load tries
members in declaration order and returns the first that fits, so the two spell
different types. A cache keyed on the type object alone serves whichever order the
process happened to build first — which is why every test here exercises both orders
in one interpreter, and why asserting a single order proves nothing.
"""

import dataclasses
import json

import pytest

from .conftest import Serializer


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Narrow:
    a: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Wide:
    a: int
    extra: str = "default"


# Both orders match the same payload, so only declaration order decides the outcome.
BOTH = b'{"a":1,"extra":"given"}'
NARROW_FIRST = Narrow | Wide
WIDE_FIRST = Wide | Narrow


class TestRootUnionMemberOrder:
    def test_narrow_first_then_wide_first(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")

        assert impl.load(NARROW_FIRST, BOTH) == Narrow(a=1)  # type: ignore[arg-type]
        assert impl.load(WIDE_FIRST, BOTH) == Wide(a=1, extra="given")  # type: ignore[arg-type]

    def test_wide_first_then_narrow_first(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")

        assert impl.load(WIDE_FIRST, BOTH) == Wide(a=1, extra="given")  # type: ignore[arg-type]
        assert impl.load(NARROW_FIRST, BOTH) == Narrow(a=1)  # type: ignore[arg-type]

    def test_optional_union_keeps_order(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")

        assert impl.load(Narrow | Wide | None, BOTH) == Narrow(a=1)  # type: ignore[arg-type]
        assert impl.load(Wide | Narrow | None, BOTH) == Wide(a=1, extra="given")  # type: ignore[arg-type]

    def test_dump_keeps_order(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")

        assert json.loads(impl.dump(NARROW_FIRST, Narrow(a=1))) == {"a": 1}  # type: ignore[arg-type]
        assert json.loads(impl.dump(WIDE_FIRST, Wide(a=1, extra="given"))) == {"a": 1, "extra": "given"}  # type: ignore[arg-type]


class TestUnionInsideRootCollectionMemberOrder:
    def test_list_of_union(self, impl: Serializer) -> None:
        if not impl.supports_root_non_dataclasses:
            pytest.skip("does not support root non-dataclasses")

        assert impl.load(list[Narrow | Wide], b"[" + BOTH + b"]") == [Narrow(a=1)]
        assert impl.load(list[Wide | Narrow], b"[" + BOTH + b"]") == [Wide(a=1, extra="given")]

    def test_dict_of_union(self, impl: Serializer) -> None:
        if not impl.supports_root_non_dataclasses:
            pytest.skip("does not support root non-dataclasses")

        assert impl.load(dict[str, Narrow | Wide], b'{"k":' + BOTH + b"}") == {"k": Narrow(a=1)}
        assert impl.load(dict[str, Wide | Narrow], b'{"k":' + BOTH + b"}") == {"k": Wide(a=1, extra="given")}


# A type alias is a distinct object per declaration, so its identity carries the member
# order even though the two values it wraps compare equal.
type NarrowFirstAlias = Narrow | Wide
type WideFirstAlias = Wide | Narrow

# The alias value can be arbitrarily deep; keying it by identity does not care.
type NarrowFirstDeep = Narrow | Wide | list[Narrow | Wide]
type WideFirstDeep = Wide | Narrow | list[Wide | Narrow]


class TestUnionBehindTypeAlias:
    def test_both_aliases_in_one_process(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")

        assert impl.load(NarrowFirstAlias, BOTH) == Narrow(a=1)  # type: ignore[arg-type]
        assert impl.load(WideFirstAlias, BOTH) == Wide(a=1, extra="given")  # type: ignore[arg-type]

    def test_alias_inside_a_root_collection(self, impl: Serializer) -> None:
        if not impl.supports_root_non_dataclasses:
            pytest.skip("does not support root non-dataclasses")

        assert impl.load(list[NarrowFirstAlias], b"[" + BOTH + b"]") == [Narrow(a=1)]
        assert impl.load(list[WideFirstAlias], b"[" + BOTH + b"]") == [Wide(a=1, extra="given")]

    def test_alias_over_a_union_that_also_contains_a_collection(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")

        assert impl.load(NarrowFirstDeep, BOTH) == Narrow(a=1)  # type: ignore[arg-type]
        assert impl.load(WideFirstDeep, BOTH) == Wide(a=1, extra="given")  # type: ignore[arg-type]
