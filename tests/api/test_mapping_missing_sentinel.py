"""End-to-end check that real webargs.MultiDictProxy returns marshmallow.missing for
absent keys and that mr.nuked.load handles it. The sentinel-handling mechanism itself
is covered through the standard impl fixture's NukedMissingSentinelSerializer variant
across the entire load suite — this file validates the webargs integration story.
"""

import dataclasses

from multidict import MultiDict
from webargs.multidictproxy import MultiDictProxy

import marshmallow_recipe as mr


def test_real_webargs_multidictproxy() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Q:
        company_id: str
        status: list[str] | None = None
        limit: int | None = None

    schema = mr.nuked.schema(Q)
    proxy = MultiDictProxy(MultiDict([("company_id", "abc")]), schema)
    assert mr.nuked.load(Q, proxy) == Q(company_id="abc", status=None, limit=None)
