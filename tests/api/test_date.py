import datetime

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithDateInvalidError,
    WithDateMissing,
    WithDateNoneError,
    WithDateRequiredError,
    WithDateTwoValidators,
    WithDateValidation,
)


class TestDateDump:
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (
                ValueOf[datetime.date],
                ValueOf[datetime.date](value=datetime.date(2025, 12, 26)),
                b'{"value":"2025-12-26"}',
            ),
            (
                ValueOf[datetime.date],
                ValueOf[datetime.date](value=datetime.datetime(2025, 12, 26, 10, 30, 45)),
                b'{"value":"2025-12-26"}',
            ),
            (OptionalValueOf[datetime.date], OptionalValueOf[datetime.date](value=None), b"{}"),
            (
                OptionalValueOf[datetime.date],
                OptionalValueOf[datetime.date](value=datetime.date(2025, 12, 26)),
                b'{"value":"2025-12-26"}',
            ),
            (WithDateMissing, WithDateMissing(), b"{}"),
            (WithDateMissing, WithDateMissing(value=datetime.date(2025, 12, 26)), b'{"value":"2025-12-26"}'),
        ],
    )
    def test_dump(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalValueOf[datetime.date](value=None), None, b"{}"),
            (OptionalValueOf[datetime.date](value=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalValueOf[datetime.date](value=None), mr.NoneValueHandling.INCLUDE, b'{"value":null}'),
            (
                OptionalValueOf[datetime.date](value=datetime.date(2025, 12, 26)),
                mr.NoneValueHandling.INCLUDE,
                b'{"value":"2025-12-26"}',
            ),
        ],
    )
    def test_none_handling(
        self,
        impl: Serializer,
        obj: OptionalValueOf[datetime.date],
        none_value_handling: mr.NoneValueHandling | None,
        expected: bytes,
    ) -> None:
        if none_value_handling is None:
            result = impl.dump(OptionalValueOf[datetime.date], obj)
        else:
            result = impl.dump(OptionalValueOf[datetime.date], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ValueOf[datetime.date](**{"value": "2024-01-01"}), id="string"),  # type: ignore[arg-type]
            pytest.param(ValueOf[datetime.date](**{"value": 123}), id="int"),  # type: ignore[arg-type]
        ],
    )
    def test_dump_invalid_type(self, impl: Serializer, obj: ValueOf[datetime.date]) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[datetime.date], obj)


class TestDateLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (
                ValueOf[datetime.date],
                b'{"value":"2025-12-26"}',
                ValueOf[datetime.date](value=datetime.date(2025, 12, 26)),
            ),
            (OptionalValueOf[datetime.date], b'{"value":null}', OptionalValueOf[datetime.date](value=None)),
            (OptionalValueOf[datetime.date], b"{}", OptionalValueOf[datetime.date](value=None)),
            (
                OptionalValueOf[datetime.date],
                b'{"value":"2025-12-26"}',
                OptionalValueOf[datetime.date](value=datetime.date(2025, 12, 26)),
            ),
            (WithDateValidation, b'{"value":"2020-06-15"}', WithDateValidation(value=datetime.date(2020, 6, 15))),
            (WithDateTwoValidators, b'{"value":"2050-06-15"}', WithDateTwoValidators(value=datetime.date(2050, 6, 15))),
            (WithDateMissing, b"{}", WithDateMissing()),
            (WithDateMissing, b'{"value":"2025-12-26"}', WithDateMissing(value=datetime.date(2025, 12, 26))),
        ],
    )
    def test_load(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "schema_type", "expected_messages"),
        [
            pytest.param(
                b'{"value":"1999-12-31"}', WithDateValidation, {"value": ["Invalid value."]}, id="validation_fail"
            ),
            pytest.param(
                b'{"value":"1999-12-31"}',
                WithDateTwoValidators,
                {"value": ["Invalid value."]},
                id="two_validators_first_fails",
            ),
            pytest.param(
                b'{"value":"2150-06-15"}',
                WithDateTwoValidators,
                {"value": ["Invalid value."]},
                id="two_validators_second_fails",
            ),
            pytest.param(
                b"{}", WithDateRequiredError, {"value": ["Custom required message"]}, id="custom_required_error"
            ),
            pytest.param(
                b'{"value":null}', WithDateNoneError, {"value": ["Custom none message"]}, id="custom_none_error"
            ),
            pytest.param(
                b'{"value":"not-a-date"}',
                WithDateInvalidError,
                {"value": ["Custom invalid message"]},
                id="custom_invalid_error",
            ),
            pytest.param(
                b'{"value":"not-a-date"}', ValueOf[datetime.date], {"value": ["Not a valid date."]}, id="invalid_format"
            ),
            pytest.param(
                b'{"value":12345}', ValueOf[datetime.date], {"value": ["Not a valid date."]}, id="wrong_type_int"
            ),
            pytest.param(
                b'{"value":["2025-12-26"]}',
                ValueOf[datetime.date],
                {"value": ["Not a valid date."]},
                id="wrong_type_list",
            ),
            pytest.param(
                b"{}", ValueOf[datetime.date], {"value": ["Missing data for required field."]}, id="missing_required"
            ),
        ],
    )
    def test_load_error(
        self, impl: Serializer, data: bytes, schema_type: type, expected_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == expected_messages
