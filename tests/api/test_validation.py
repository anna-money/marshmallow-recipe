import marshmallow
import pytest

import marshmallow_recipe as mr


class TestEmailValidate:
    @pytest.mark.parametrize(
        "email", ["user@example.com", "test.user+tag@domain.co.uk", "user@localhost", "backup@domain.org"]
    )
    def test_valid_email(self, email: str) -> None:
        validator = mr.email_validate()
        validator(email)

    @pytest.mark.parametrize(
        "email", ["", "notanemail", "user@", "@domain.com", '"very.unusual.@.unusual.com"@example.com']
    )
    def test_invalid_email(self, email: str) -> None:
        validator = mr.email_validate()
        with pytest.raises(marshmallow.ValidationError) as exc:
            validator(email)
        assert exc.value.messages == ["Not a valid email address."]

    def test_custom_error_message(self) -> None:
        validator = mr.email_validate(error="Invalid email: {input}")
        with pytest.raises(marshmallow.ValidationError) as exc:
            validator("invalid")
        assert exc.value.messages == ["Invalid email: invalid"]


class TestRegexpValidate:
    @pytest.mark.parametrize("value", ["abc", "hello", "world"])
    def test_valid_pattern(self, value: str) -> None:
        validator = mr.regexp_validate(r"^[a-z]+$")
        validator(value)

    @pytest.mark.parametrize("value", ["42", "ABC", "hello123", ""])
    def test_invalid_pattern(self, value: str) -> None:
        validator = mr.regexp_validate(r"^[a-z]+$")
        with pytest.raises(marshmallow.ValidationError) as exc:
            validator(value)
        assert exc.value.messages == ["String does not match expected pattern."]

    def test_custom_error_message(self) -> None:
        validator = mr.regexp_validate(r"^[a-z]+$", error="Must be lowercase letters only")
        with pytest.raises(marshmallow.ValidationError) as exc:
            validator("123")
        assert exc.value.messages == ["Must be lowercase letters only"]


class TestValidate:
    def test_valid_value(self) -> None:
        validator = mr.validate(lambda x: x > 0, error="Must be positive")
        validator(42)

    def test_invalid_value(self) -> None:
        validator = mr.validate(lambda x: x > 0, error="Must be positive")
        with pytest.raises(marshmallow.ValidationError) as exc:
            validator(-1)
        assert exc.value.messages == ["Must be positive"]


class TestGetValidationFieldErrors:
    def test_simple_error(self) -> None:
        error = marshmallow.ValidationError({"value": ["Not a valid integer."]})
        result = mr.get_validation_field_errors(error)
        assert result == [mr.ValidationFieldError(name="value", error="Not a valid integer.")]

    def test_nested_error(self) -> None:
        error = marshmallow.ValidationError({"nested": {"field": ["Error message"]}})
        result = mr.get_validation_field_errors(error)
        assert result == [
            mr.ValidationFieldError(
                name="nested", nested_errors=[mr.ValidationFieldError(name="field", error="Error message")]
            )
        ]

    def test_complex_nested_error(self) -> None:
        error = marshmallow.ValidationError(
            {
                "value": ["Not a valid integer."],
                "values": {"0": ["Not a valid integer."]},
                "nested": {"value": ["Not a valid integer."], "values": {"0": ["Not a valid integer."]}},
            }
        )
        result = mr.get_validation_field_errors(error)
        assert result == [
            mr.ValidationFieldError(
                name="nested",
                nested_errors=[
                    mr.ValidationFieldError(name="value", error="Not a valid integer."),
                    mr.ValidationFieldError(
                        name="values", nested_errors=[mr.ValidationFieldError(name="0", error="Not a valid integer.")]
                    ),
                ],
            ),
            mr.ValidationFieldError(name="value", error="Not a valid integer."),
            mr.ValidationFieldError(
                name="values", nested_errors=[mr.ValidationFieldError(name="0", error="Not a valid integer.")]
            ),
        ]
