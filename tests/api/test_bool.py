import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithBoolDefault,
    WithBoolInvalidError,
    WithBoolMissing,
    WithBoolNoneError,
    WithBoolRequiredError,
    WithBoolTwoValidators,
    WithBoolValidation,
)


class TestBoolDump:
    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(ValueOf[bool](value=True), b'{"value":true}', id="true"),
            pytest.param(ValueOf[bool](value=False), b'{"value":false}', id="false"),
        ],
    )
    def test_value(self, impl: Serializer, obj: ValueOf[bool], expected: bytes) -> None:
        result = impl.dump(ValueOf[bool], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(OptionalValueOf[bool](value=None), b"{}", id="none"),
            pytest.param(OptionalValueOf[bool](value=True), b'{"value":true}', id="value"),
        ],
    )
    def test_optional(self, impl: Serializer, obj: OptionalValueOf[bool], expected: bytes) -> None:
        result = impl.dump(OptionalValueOf[bool], obj)
        assert result == expected

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithBoolDefault(value=False)
        result = impl.dump(WithBoolDefault, obj)
        assert result == b'{"value":false}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=None)
        result = impl.dump(OptionalValueOf[bool], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=None)
        result = impl.dump(OptionalValueOf[bool], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=None)
        result = impl.dump(OptionalValueOf[bool], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=True)
        result = impl.dump(OptionalValueOf[bool], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":true}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(WithBoolMissing(), b"{}", id="omitted"),
            pytest.param(WithBoolMissing(value=True), b'{"value":true}', id="provided"),
        ],
    )
    def test_missing(self, impl: Serializer, obj: WithBoolMissing, expected: bytes) -> None:
        result = impl.dump(WithBoolMissing, obj)
        assert result == expected


class TestBoolLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":true}', ValueOf[bool](value=True), id="true"),
            pytest.param(b'{"value":false}', ValueOf[bool](value=False), id="false"),
            pytest.param(b'{"value":0}', ValueOf[bool](value=False), id="zero"),
            pytest.param(b'{"value":1}', ValueOf[bool](value=True), id="one"),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: ValueOf[bool]) -> None:
        result = impl.load(ValueOf[bool], data)
        assert result == expected

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolValidation, data)
        assert result == WithBoolValidation(value=True)

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolTwoValidators, data)
        assert result == WithBoolTwoValidators(value=True)

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":null}', OptionalValueOf[bool](value=None), id="none"),
            pytest.param(b"{}", OptionalValueOf[bool](value=None), id="missing"),
            pytest.param(b'{"value":true}', OptionalValueOf[bool](value=True), id="value"),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalValueOf[bool]) -> None:
        result = impl.load(OptionalValueOf[bool], data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b"{}", WithBoolDefault(value=True), id="omitted"),
            pytest.param(b'{"value":false}', WithBoolDefault(value=False), id="provided"),
        ],
    )
    def test_default(self, impl: Serializer, data: bytes, expected: WithBoolDefault) -> None:
        result = impl.load(WithBoolDefault, data)
        assert result == expected

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-bool"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        "data", [pytest.param(b'{"value":"not_bool"}', id="string"), pytest.param(b'{"value":[true,false]}', id="list")]
    )
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bool], data)
        assert exc.value.messages == {"value": ["Not a valid boolean."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bool], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b"{}", WithBoolMissing(), id="omitted"),
            pytest.param(b'{"value":true}', WithBoolMissing(value=True), id="provided"),
        ],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithBoolMissing) -> None:
        result = impl.load(WithBoolMissing, data)
        assert result == expected


class TestBoolDumpInvalidType:
    """Test that invalid types in bool fields raise ValidationError on dump."""

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ValueOf[bool](**{"value": "not a bool"}), id="string"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bool](**{"value": 1}), id="int"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bool](**{"value": []}), id="list"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ValueOf[bool]) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[bool], obj)
