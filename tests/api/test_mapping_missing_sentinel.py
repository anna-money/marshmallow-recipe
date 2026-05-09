import dataclasses
from typing import Any

import marshmallow as ma
from multidict import MultiDict
from webargs.multidictproxy import MultiDictProxy

import marshmallow_recipe as mr


class _MissingMapping(dict):
    """Emulates webargs.MultiDictProxy: __getitem__ returns ma.missing for absent keys."""

    def __getitem__(self, k: Any) -> Any:
        if super().__contains__(k):
            return super().__getitem__(k)
        return ma.missing


class TestMappingMissingSentinel:
    def test_root_optional_field_absent(self) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Q:
            a: str
            b: int | None = None

        result = mr.nuked.load(Q, _MissingMapping(a="x"))
        assert result == Q(a="x", b=None)

    def test_nested_optional_field_absent(self) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Inner:
            x: str
            y: int | None = None

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Outer:
            inner: Inner

        result = mr.nuked.load(Outer, _MissingMapping(inner=_MissingMapping(x="hello")))
        assert result == Outer(inner=Inner(x="hello", y=None))

    def test_real_webargs_multidictproxy(self) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Q:
            company_id: str
            status: list[str] | None = None
            limit: int | None = None

        schema = mr.nuked.schema(Q)
        proxy = MultiDictProxy(MultiDict([("company_id", "abc")]), schema)
        assert mr.nuked.load(Q, proxy) == Q(company_id="abc", status=None, limit=None)
