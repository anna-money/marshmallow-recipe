import dataclasses
import datetime
import decimal
import enum
import importlib.metadata
import uuid
from typing import Any

import marshmallow
import pytest

import marshmallow_recipe as mr

_MARSHMALLOW_VERSION_MAJOR = int(importlib.metadata.version("marshmallow").split(".")[0])


class Color(str, enum.Enum):
    RED = "red"
    BLUE = "blue"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetime:
    value: datetime.datetime


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithOptionalDatetime:
    value: datetime.datetime | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeIso:
    value: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="iso"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeTimestamp:
    value: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="timestamp"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeCustomFormat:
    value: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y/%m/%d"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDate:
    value: datetime.date


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTime:
    value: datetime.time


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStr:
    value: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithInt:
    value: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloat:
    value: float


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBool:
    value: bool


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimal:
    value: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUuid:
    value: uuid.UUID


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithList:
    value: list[str]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSet:
    value: set[str]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFrozenSet:
    value: frozenset[str]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDict:
    value: dict[str, int]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithEnum:
    value: Color


def _get_schema_via_bake_schema(cls: type) -> marshmallow.Schema:
    return mr.bake_schema(cls)()


def _get_schema_via_schema(cls: type) -> marshmallow.Schema:
    return mr.schema(cls)


def _get_schema_via_nuked_schema(cls: type) -> marshmallow.Schema:
    return mr.nuked.schema(cls)


def _field2property(field: marshmallow.fields.Field) -> dict[str, Any]:
    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin

    spec = APISpec(title="test", version="0.1.0", openapi_version="3.0.0", plugins=[])
    plugin = MarshmallowPlugin()
    plugin.init_spec(spec)
    assert plugin.converter is not None
    return plugin.converter.field2property(field)


@pytest.fixture(
    params=[_get_schema_via_bake_schema, _get_schema_via_schema, _get_schema_via_nuked_schema],
    ids=["bake_schema", "schema", "nuked_schema"],
)
def get_schema(request: pytest.FixtureRequest) -> Any:
    return request.param


class TestOpenApiType:
    @pytest.mark.parametrize(
        ("cls", "expected"),
        [
            (WithDatetime, {"type": "string", "format": "date-time"}),
            (WithDatetimeIso, {"type": "string", "format": "date-time"}),
            (WithDate, {"type": "string", "format": "date"}),
            (WithTime, {"type": "string"}),
            (WithStr, {"type": "string"}),
            (WithInt, {"type": "integer", "format": "int32"}),
            (WithFloat, {"type": "number", "format": "float"}),
            (WithBool, {"type": "boolean"}),
            (WithDecimal, {"type": "number"}),
            (WithUuid, {"type": "string", "format": "uuid"}),
        ],
        ids=["datetime", "datetime_iso", "date", "time", "str", "int", "float", "bool", "decimal", "uuid"],
    )
    def test_simple_type(self, get_schema: Any, cls: type, expected: dict[str, Any]) -> None:
        schema = get_schema(cls)
        result = _field2property(schema.fields["value"])
        assert result == expected

    def test_datetime_optional(self, get_schema: Any) -> None:
        schema = get_schema(WithOptionalDatetime)
        result = _field2property(schema.fields["value"])
        if _MARSHMALLOW_VERSION_MAJOR >= 3:
            assert result == {"type": "string", "format": "date-time", "nullable": True}
        else:
            assert result == {"type": "string", "format": "date-time", "x-nullable": True}

    def test_list(self, get_schema: Any) -> None:
        schema = get_schema(WithList)
        result = _field2property(schema.fields["value"])
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_set(self, get_schema: Any) -> None:
        schema = get_schema(WithSet)
        result = _field2property(schema.fields["value"])
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_frozenset(self, get_schema: Any) -> None:
        schema = get_schema(WithFrozenSet)
        result = _field2property(schema.fields["value"])
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_dict(self, get_schema: Any) -> None:
        schema = get_schema(WithDict)
        result = _field2property(schema.fields["value"])
        if _MARSHMALLOW_VERSION_MAJOR >= 3:
            assert result == {"type": "object", "additionalProperties": {"type": "integer", "format": "int32"}}
        else:
            assert result == {"type": "object"}

    def test_enum(self, get_schema: Any) -> None:
        schema = get_schema(WithEnum)
        result = _field2property(schema.fields["value"])
        assert result["enum"] == ["red", "blue"]
