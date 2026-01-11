import datetime

import marshmallow
import pytest

from .conftest import (
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
        ("value", "expected"),
        [
            pytest.param(datetime.date(2025, 12, 26), b'{"value":"2025-12-26"}', id="standard"),
            pytest.param(datetime.date(2025, 1, 1), b'{"value":"2025-01-01"}', id="year_start"),
            pytest.param(datetime.date(2025, 12, 31), b'{"value":"2025-12-31"}', id="year_end"),
            pytest.param(datetime.date(2024, 2, 29), b'{"value":"2024-02-29"}', id="leap_year"),
            pytest.param(datetime.date(2000, 2, 29), b'{"value":"2000-02-29"}', id="leap_year_2000"),
            pytest.param(datetime.date(1900, 2, 28), b'{"value":"1900-02-28"}', id="non_leap_1900"),
            pytest.param(datetime.date(2025, 1, 31), b'{"value":"2025-01-31"}', id="jan_31"),
            pytest.param(datetime.date(2025, 4, 30), b'{"value":"2025-04-30"}', id="apr_30"),
            pytest.param(datetime.date(2025, 2, 28), b'{"value":"2025-02-28"}', id="feb_28"),
            pytest.param(datetime.date(1970, 1, 1), b'{"value":"1970-01-01"}', id="unix_epoch"),
            pytest.param(datetime.date(2000, 1, 1), b'{"value":"2000-01-01"}', id="y2k"),
            pytest.param(datetime.date(2999, 12, 31), b'{"value":"2999-12-31"}', id="far_future"),
            pytest.param(datetime.date(1, 1, 1), b'{"value":"0001-01-01"}', id="min_date"),
            pytest.param(datetime.date(9999, 12, 31), b'{"value":"9999-12-31"}', id="max_date"),
            # datetime.datetime inherits from datetime.date
            pytest.param(datetime.datetime(2025, 12, 26, 10, 30, 45), b'{"value":"2025-12-26"}', id="datetime_as_date"),
        ],
    )
    def test_value(self, impl: Serializer, value: datetime.date, expected: bytes) -> None:
        obj = ValueOf[datetime.date](value=value)
        result = impl.dump(ValueOf[datetime.date], obj)
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        obj = WithDateMissing()
        result = impl.dump(WithDateMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithDateMissing(value=datetime.date(2025, 12, 26))
        result = impl.dump(WithDateMissing, obj)
        assert result == b'{"value":"2025-12-26"}'


class TestDateLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            # Standard ISO format
            pytest.param(b'{"value":"2025-12-26"}', datetime.date(2025, 12, 26), id="standard"),
            # Edge cases: year boundaries
            pytest.param(b'{"value":"2025-01-01"}', datetime.date(2025, 1, 1), id="year_start"),
            pytest.param(b'{"value":"2025-12-31"}', datetime.date(2025, 12, 31), id="year_end"),
            # Leap years
            pytest.param(b'{"value":"2024-02-29"}', datetime.date(2024, 2, 29), id="leap_year"),
            pytest.param(b'{"value":"2000-02-29"}', datetime.date(2000, 2, 29), id="leap_year_2000"),
            # Non-leap year February
            pytest.param(b'{"value":"2025-02-28"}', datetime.date(2025, 2, 28), id="feb_28"),
            pytest.param(b'{"value":"1900-02-28"}', datetime.date(1900, 2, 28), id="non_leap_1900"),
            # Month boundaries
            pytest.param(b'{"value":"2025-01-31"}', datetime.date(2025, 1, 31), id="jan_31"),
            pytest.param(b'{"value":"2025-03-31"}', datetime.date(2025, 3, 31), id="mar_31"),
            pytest.param(b'{"value":"2025-04-30"}', datetime.date(2025, 4, 30), id="apr_30"),
            pytest.param(b'{"value":"2025-06-30"}', datetime.date(2025, 6, 30), id="jun_30"),
            # Unix epoch
            pytest.param(b'{"value":"1970-01-01"}', datetime.date(1970, 1, 1), id="unix_epoch"),
            # Y2K
            pytest.param(b'{"value":"2000-01-01"}', datetime.date(2000, 1, 1), id="y2k"),
            # Far future
            pytest.param(b'{"value":"2999-12-31"}', datetime.date(2999, 12, 31), id="far_future"),
            # Min/max dates
            pytest.param(b'{"value":"0001-01-01"}', datetime.date(1, 1, 1), id="min_date"),
            pytest.param(b'{"value":"9999-12-31"}', datetime.date(9999, 12, 31), id="max_date"),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: datetime.date) -> None:
        result = impl.load(ValueOf[datetime.date], data)
        assert result == ValueOf[datetime.date](value=expected)

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"2020-06-15"}'
        result = impl.load(WithDateValidation, data)
        assert result == WithDateValidation(value=datetime.date(2020, 6, 15))

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":"1999-12-31"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"2050-06-15"}'
        result = impl.load(WithDateTwoValidators, data)
        assert result == WithDateTwoValidators(value=datetime.date(2050, 6, 15))

    @pytest.mark.parametrize("data", [b'{"value":"1999-12-31"}', b'{"value":"2150-06-15"}'])
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-date"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize("data", [b'{"value":"not-a-date"}', b'{"value":12345}', b'{"value":["2025-12-26"]}'])
    def test_invalid_format(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.date], data)
        assert exc.value.messages == {"value": ["Not a valid date."]}

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"2025-02-29"}', id="feb_29_non_leap"),
            pytest.param(b'{"value":"2025-04-31"}', id="apr_31"),
            pytest.param(b'{"value":"2025-06-31"}', id="jun_31"),
            pytest.param(b'{"value":"2025-09-31"}', id="sep_31"),
            pytest.param(b'{"value":"2025-11-31"}', id="nov_31"),
            pytest.param(b'{"value":"2025-00-01"}', id="month_zero"),
            pytest.param(b'{"value":"2025-13-01"}', id="month_13"),
            pytest.param(b'{"value":"2025-01-00"}', id="day_zero"),
            pytest.param(b'{"value":"2025-01-32"}', id="day_32"),
        ],
    )
    def test_invalid_date_values(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.date], data)
        assert exc.value.messages == {"value": ["Not a valid date."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithDateMissing, data)
        assert result == WithDateMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"2025-12-26"}'
        result = impl.load(WithDateMissing, data)
        assert result == WithDateMissing(value=datetime.date(2025, 12, 26))


class TestDateDumpInvalidType:
    """Test that invalid types in date fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["2024-01-01", 123])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ValueOf[datetime.date](**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[datetime.date], obj)


class TestDateEdgeCases:
    """Test date edge cases with century boundaries and special dates."""

    def test_century_boundary_2100_non_leap(self, impl: Serializer) -> None:
        # 2100 is not a leap year (divisible by 100 but not 400)
        obj = ValueOf[datetime.date](value=datetime.date(2100, 2, 28))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    def test_century_boundary_2000_leap(self, impl: Serializer) -> None:
        # 2000 is a leap year (divisible by 400)
        obj = ValueOf[datetime.date](value=datetime.date(2000, 2, 29))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    def test_year_1_min_date(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.date](value=datetime.date(1, 1, 1))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    def test_year_9999_max_date(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.date](value=datetime.date(9999, 12, 31))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    @pytest.mark.parametrize(
        ("year", "month", "expected_day"),
        [
            pytest.param(2024, 1, 31, id="jan"),
            pytest.param(2024, 2, 29, id="feb_leap"),
            pytest.param(2023, 2, 28, id="feb_non_leap"),
            pytest.param(2024, 3, 31, id="mar"),
            pytest.param(2024, 4, 30, id="apr"),
            pytest.param(2024, 5, 31, id="may"),
            pytest.param(2024, 6, 30, id="jun"),
            pytest.param(2024, 7, 31, id="jul"),
            pytest.param(2024, 8, 31, id="aug"),
            pytest.param(2024, 9, 30, id="sep"),
            pytest.param(2024, 10, 31, id="oct"),
            pytest.param(2024, 11, 30, id="nov"),
            pytest.param(2024, 12, 31, id="dec"),
        ],
    )
    def test_last_day_of_each_month(self, impl: Serializer, year: int, month: int, expected_day: int) -> None:
        date_val = datetime.date(year, month, expected_day)
        obj = ValueOf[datetime.date](value=date_val)
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    def test_leap_year_century_1600(self, impl: Serializer) -> None:
        # 1600 is a leap year (divisible by 400)
        obj = ValueOf[datetime.date](value=datetime.date(1600, 2, 29))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    def test_non_leap_year_century_1900(self, impl: Serializer) -> None:
        # 1900 is not a leap year (divisible by 100 but not 400)
        obj = ValueOf[datetime.date](value=datetime.date(1900, 2, 28))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    def test_typical_dst_transition_date(self, impl: Serializer) -> None:
        # March 10, 2024 - typical DST transition date
        obj = ValueOf[datetime.date](value=datetime.date(2024, 3, 10))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj

    def test_new_year_boundary(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.date](value=datetime.date(2024, 12, 31))
        result = impl.dump(ValueOf[datetime.date], obj)
        loaded = impl.load(ValueOf[datetime.date], result)
        assert loaded == obj
