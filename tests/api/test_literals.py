import marshmallow
import pytest

from .conftest import (
    Serializer,
    WithIntLiteral,
    WithIntLiteralMissing,
    WithOptionalStrLiteral,
    WithStrLiteral,
    WithStrLiteralDefault,
    WithStrLiteralMissing,
)


class TestLiteralDump:
    def test_str_literal(self, impl: Serializer) -> None:
        obj = WithStrLiteral(value="a")
        result = impl.dump(WithStrLiteral, obj)
        assert result == b'{"value":"a"}'

    def test_str_literal_other_value(self, impl: Serializer) -> None:
        obj = WithStrLiteral(value="c")
        result = impl.dump(WithStrLiteral, obj)
        assert result == b'{"value":"c"}'

    def test_int_literal(self, impl: Serializer) -> None:
        obj = WithIntLiteral(value=1)
        result = impl.dump(WithIntLiteral, obj)
        assert result == b'{"value":1}'

    def test_int_literal_other_value(self, impl: Serializer) -> None:
        obj = WithIntLiteral(value=3)
        result = impl.dump(WithIntLiteral, obj)
        assert result == b'{"value":3}'

    def test_optional_str_literal_none(self, impl: Serializer) -> None:
        obj = WithOptionalStrLiteral(value=None)
        result = impl.dump(WithOptionalStrLiteral, obj)
        assert result == b"{}"

    def test_optional_str_literal_value(self, impl: Serializer) -> None:
        obj = WithOptionalStrLiteral(value="x")
        result = impl.dump(WithOptionalStrLiteral, obj)
        assert result == b'{"value":"x"}'

    def test_str_literal_default(self, impl: Serializer) -> None:
        obj = WithStrLiteralDefault()
        result = impl.dump(WithStrLiteralDefault, obj)
        assert result == b'{"value":"a"}'

    def test_str_literal_missing(self, impl: Serializer) -> None:
        obj = WithStrLiteralMissing()
        result = impl.dump(WithStrLiteralMissing, obj)
        assert result == b"{}"

    def test_str_literal_missing_with_value(self, impl: Serializer) -> None:
        obj = WithStrLiteralMissing(value="b")
        result = impl.dump(WithStrLiteralMissing, obj)
        assert result == b'{"value":"b"}'

    def test_int_literal_missing(self, impl: Serializer) -> None:
        obj = WithIntLiteralMissing()
        result = impl.dump(WithIntLiteralMissing, obj)
        assert result == b"{}"

    def test_int_literal_missing_with_value(self, impl: Serializer) -> None:
        obj = WithIntLiteralMissing(value=2)
        result = impl.dump(WithIntLiteralMissing, obj)
        assert result == b'{"value":2}'


class TestLiteralLoad:
    def test_str_literal(self, impl: Serializer) -> None:
        data = b'{"value":"b"}'
        result = impl.load(WithStrLiteral, data)
        assert result == WithStrLiteral(value="b")

    def test_int_literal(self, impl: Serializer) -> None:
        data = b'{"value":2}'
        result = impl.load(WithIntLiteral, data)
        assert result == WithIntLiteral(value=2)

    def test_optional_str_literal_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(WithOptionalStrLiteral, data)
        assert result == WithOptionalStrLiteral(value=None)

    def test_optional_str_literal_value(self, impl: Serializer) -> None:
        data = b'{"value":"y"}'
        result = impl.load(WithOptionalStrLiteral, data)
        assert result == WithOptionalStrLiteral(value="y")

    def test_optional_str_literal_missing_key(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalStrLiteral, data)
        assert result == WithOptionalStrLiteral(value=None)

    def test_str_literal_default(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrLiteralDefault, data)
        assert result == WithStrLiteralDefault(value="a")

    def test_str_literal_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":"z"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['a', 'b', 'c']"]}

    def test_int_literal_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":999}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_str_literal_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['a', 'b', 'c']"]}

    def test_int_literal_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":"not_a_number"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_int_literal_bool_rejected(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_str_literal_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteral, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_str_literal_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrLiteralMissing, data)
        assert result == WithStrLiteralMissing()

    def test_str_literal_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"a"}'
        result = impl.load(WithStrLiteralMissing, data)
        assert result == WithStrLiteralMissing(value="a")
