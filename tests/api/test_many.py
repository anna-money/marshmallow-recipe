import pytest

import marshmallow_recipe as mr

from .conftest import OptionalValueOf, Serializer, ValueOf


@pytest.fixture
def skip_if_no_many(impl: Serializer) -> None:
    if not impl.supports_many:
        pytest.skip("many not supported")


@pytest.mark.usefixtures("skip_if_no_many")
class TestManyDump:
    def test_basic(self, impl: Serializer) -> None:
        objs = [ValueOf[int](value=1), ValueOf[int](value=2), ValueOf[int](value=3)]
        result = impl.dump_many(ValueOf[int], objs)
        assert result == b'[{"value":1},{"value":2},{"value":3}]'

    def test_empty(self, impl: Serializer) -> None:
        objs: list[ValueOf[int]] = []
        result = impl.dump_many(ValueOf[int], objs)
        assert result == b"[]"

    def test_single(self, impl: Serializer) -> None:
        objs = [ValueOf[str](value="hello")]
        result = impl.dump_many(ValueOf[str], objs)
        assert result == b'[{"value":"hello"}]'

    def test_none_handling_include(self, impl: Serializer) -> None:
        objs = [OptionalValueOf[str](value="hello"), OptionalValueOf[str](value=None)]
        result = impl.dump_many(OptionalValueOf[str], objs, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'[{"value":"hello"},{"value":null}]'

    def test_none_handling_ignore(self, impl: Serializer) -> None:
        objs = [OptionalValueOf[str](value="hello"), OptionalValueOf[str](value=None)]
        result = impl.dump_many(OptionalValueOf[str], objs, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b'[{"value":"hello"},{}]'


@pytest.mark.usefixtures("skip_if_no_many")
class TestManyLoad:
    def test_basic(self, impl: Serializer) -> None:
        data = b'[{"value":1},{"value":2},{"value":3}]'
        result = impl.load_many(ValueOf[int], data)
        assert result == [ValueOf[int](value=1), ValueOf[int](value=2), ValueOf[int](value=3)]

    def test_empty(self, impl: Serializer) -> None:
        data = b"[]"
        result = impl.load_many(ValueOf[int], data)
        assert result == []

    def test_single(self, impl: Serializer) -> None:
        data = b'[{"value":"world"}]'
        result = impl.load_many(ValueOf[str], data)
        assert result == [ValueOf[str](value="world")]
