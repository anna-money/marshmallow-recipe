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


@pytest.mark.usefixtures("skip_if_no_many")
class TestManyEdgeCases:
    """Test many (batch) operations with edge cases."""

    def test_dump_1000_items(self, impl: Serializer) -> None:
        objs = [ValueOf[int](value=i) for i in range(1000)]
        result = impl.dump_many(ValueOf[int], objs)
        loaded = impl.load_many(ValueOf[int], result)
        assert len(loaded) == 1000
        assert loaded[0].value == 0
        assert loaded[999].value == 999

    def test_load_1000_items(self, impl: Serializer) -> None:
        data = b"[" + b",".join(f'{{"value":{i}}}'.encode() for i in range(1000)) + b"]"
        result = impl.load_many(ValueOf[int], data)
        assert len(result) == 1000
        assert result[0].value == 0
        assert result[999].value == 999

    def test_dump_big_ints(self, impl: Serializer) -> None:
        big_values = [2**63, 2**100, -(2**63) - 1]
        objs = [ValueOf[int](value=v) for v in big_values]
        result = impl.dump_many(ValueOf[int], objs)
        loaded = impl.load_many(ValueOf[int], result)
        assert [obj.value for obj in loaded] == big_values

    def test_load_big_ints(self, impl: Serializer) -> None:
        big_values = [9223372036854775808, 2**100, -9223372036854775809]
        data = b"[" + b",".join(f'{{"value":{v}}}'.encode() for v in big_values) + b"]"
        result = impl.load_many(ValueOf[int], data)
        assert [obj.value for obj in result] == big_values

    def test_dump_unicode_strings(self, impl: Serializer) -> None:
        unicode_values = ["Привет", "你好", "🎉", "مرحبا", "שלום"]
        objs = [ValueOf[str](value=v) for v in unicode_values]
        result = impl.dump_many(ValueOf[str], objs)
        loaded = impl.load_many(ValueOf[str], result)
        assert [obj.value for obj in loaded] == unicode_values

    def test_dump_special_chars(self, impl: Serializer) -> None:
        special_values = ['"quoted"', "back\\slash", "new\nline", "tab\there"]
        objs = [ValueOf[str](value=v) for v in special_values]
        result = impl.dump_many(ValueOf[str], objs)
        loaded = impl.load_many(ValueOf[str], result)
        assert [obj.value for obj in loaded] == special_values

    def test_dump_empty_strings(self, impl: Serializer) -> None:
        objs = [ValueOf[str](value=""), ValueOf[str](value=""), ValueOf[str](value="")]
        result = impl.dump_many(ValueOf[str], objs)
        loaded = impl.load_many(ValueOf[str], result)
        assert all(obj.value == "" for obj in loaded)

    def test_dump_whitespace_strings(self, impl: Serializer) -> None:
        whitespace_values = ["   ", "\t\t", "\n\n", " \t\n "]
        objs = [ValueOf[str](value=v) for v in whitespace_values]
        result = impl.dump_many(ValueOf[str], objs)
        loaded = impl.load_many(ValueOf[str], result)
        assert [obj.value for obj in loaded] == whitespace_values

    def test_dump_mixed_optional_none_include(self, impl: Serializer) -> None:
        objs = [
            OptionalValueOf[str](value="hello"),
            OptionalValueOf[str](value=None),
            OptionalValueOf[str](value="world"),
            OptionalValueOf[str](value=None),
        ]
        result = impl.dump_many(OptionalValueOf[str], objs, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'[{"value":"hello"},{"value":null},{"value":"world"},{"value":null}]'

    def test_dump_all_none(self, impl: Serializer) -> None:
        objs = [OptionalValueOf[str](value=None) for _ in range(5)]
        result = impl.dump_many(OptionalValueOf[str], objs, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'[{"value":null},{"value":null},{"value":null},{"value":null},{"value":null}]'

    def test_dump_float_edge_values(self, impl: Serializer) -> None:
        float_values = [0.0, -0.0, 5e-324, 1.7976931348623157e308, -1e-100]
        objs = [ValueOf[float](value=v) for v in float_values]
        result = impl.dump_many(ValueOf[float], objs)
        loaded = impl.load_many(ValueOf[float], result)
        assert len(loaded) == 5

    def test_dump_bool_values(self, impl: Serializer) -> None:
        bool_values = [True, False, True, False, True]
        objs = [ValueOf[bool](value=v) for v in bool_values]
        result = impl.dump_many(ValueOf[bool], objs)
        loaded = impl.load_many(ValueOf[bool], result)
        assert [obj.value for obj in loaded] == bool_values

    def test_load_very_long_strings(self, impl: Serializer) -> None:
        long_str = "x" * 10000
        data = f'[{{"value":"{long_str}"}},{{"value":"{long_str}"}}]'.encode()
        result = impl.load_many(ValueOf[str], data)
        assert len(result) == 2
        assert all(obj.value == long_str for obj in result)
