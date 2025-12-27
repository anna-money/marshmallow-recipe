import abc
import json
from typing import Any

import pytest

import marshmallow_recipe as mr


class Serializer(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def dump[T](
        self,
        schema_class: type[T],
        obj: T,
        naming_case: mr.NamingCase | None = None,
        none_value_handling: str | mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
    ) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def load[T](
        self, schema_class: type[T], data: bytes | dict[str, Any], naming_case: mr.NamingCase | None = None
    ) -> T:
        raise NotImplementedError


class MarshmallowSerializer(Serializer):
    __slots__ = ()

    def dump[T](
        self,
        schema_class: type[T],
        obj: T,
        naming_case: mr.NamingCase | None = None,
        none_value_handling: str | mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
    ) -> str:
        none_handling = (
            mr.NoneValueHandling(none_value_handling) if isinstance(none_value_handling, str) else none_value_handling
        )
        result = mr.dump(
            schema_class, obj, naming_case=naming_case, none_value_handling=none_handling, decimal_places=decimal_places
        )
        return json.dumps(result, sort_keys=True)

    def load[T](
        self, schema_class: type[T], data: bytes | dict[str, Any], naming_case: mr.NamingCase | None = None
    ) -> T:
        data_dict: dict[str, Any] = json.loads(data) if isinstance(data, bytes) else data
        return mr.load(schema_class, data_dict, naming_case=naming_case)


class SpeedupSerializer(Serializer):
    __slots__ = ()

    def dump[T](
        self,
        schema_class: type[T],
        obj: T,
        naming_case: mr.NamingCase | None = None,
        none_value_handling: str | mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
    ) -> str:
        if isinstance(none_value_handling, mr.NoneValueHandling):
            none_handling = none_value_handling.value
        else:
            none_handling = none_value_handling
        result = mr.speedup.dump(
            schema_class,
            obj,
            naming_case=naming_case,
            none_value_handling=none_handling,
            decimal_places=decimal_places if decimal_places is not mr.MISSING else None,
        )
        return json.dumps(json.loads(result), sort_keys=True)

    def load[T](
        self, schema_class: type[T], data: bytes | dict[str, Any], naming_case: mr.NamingCase | None = None
    ) -> T:
        data_bytes: bytes = json.dumps(data).encode() if isinstance(data, dict) else data
        return mr.speedup.load(schema_class, data_bytes, naming_case=naming_case)


@pytest.fixture(params=[MarshmallowSerializer(), SpeedupSerializer()], ids=["marshmallow", "speedup"])
def impl(request: pytest.FixtureRequest) -> Serializer:
    return request.param
