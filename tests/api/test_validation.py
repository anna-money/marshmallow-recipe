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


class TestValidationEdgeCases:
    """Test validation edge cases with special inputs."""

    @pytest.mark.parametrize(
        "email",
        [
            pytest.param("user+tag@domain.com", id="with_plus"),
            pytest.param("user.name@domain.co.uk", id="with_dots"),
            pytest.param("user_name@domain.com", id="with_underscore"),
            pytest.param("user-name@domain.com", id="with_hyphen"),
            pytest.param("user123@domain123.com", id="with_numbers"),
            pytest.param("USER@DOMAIN.COM", id="uppercase"),
            pytest.param("user@sub.domain.com", id="subdomain"),
        ],
    )
    def test_valid_email_variants(self, email: str) -> None:
        validator = mr.email_validate()
        validator(email)

    @pytest.mark.parametrize(
        "email",
        [
            pytest.param("user@", id="no_domain"),
            pytest.param("@domain.com", id="no_local"),
            pytest.param("user@@domain.com", id="double_at"),
            pytest.param("user@domain", id="no_tld"),
            pytest.param("user name@domain.com", id="space_in_local"),
            pytest.param("user@domain .com", id="space_in_domain"),
            pytest.param("", id="empty"),
            pytest.param("   ", id="whitespace_only"),
            pytest.param("\t\n", id="control_chars"),
        ],
    )
    def test_invalid_email_variants(self, email: str) -> None:
        validator = mr.email_validate()
        with pytest.raises(marshmallow.ValidationError):
            validator(email)

    @pytest.mark.parametrize(
        ("pattern", "valid_values"),
        [
            pytest.param(r"^\d+$", ["0", "123", "9999999999"], id="digits"),
            pytest.param(r"^[A-Z]{2,4}$", ["AB", "ABC", "ABCD"], id="uppercase_letters"),
            pytest.param(r"^[\w.-]+$", ["hello", "hello.world", "hello-world"], id="word_chars"),
            pytest.param(r"^\S+$", ["no_spaces", "abc123", "!@#$%"], id="non_whitespace"),
        ],
    )
    def test_regexp_patterns(self, pattern: str, valid_values: list[str]) -> None:
        validator = mr.regexp_validate(pattern)
        for value in valid_values:
            validator(value)

    @pytest.mark.parametrize(
        ("pattern", "invalid_values"),
        [
            pytest.param(r"^\d+$", ["abc", "12.34", "12 34", ""], id="digits"),
            pytest.param(r"^[A-Z]{2,4}$", ["a", "abc", "ABCDE", "AB1"], id="uppercase_letters"),
            pytest.param(r"^\S+$", [" ", "a b", "\t", "\n"], id="non_whitespace"),
        ],
    )
    def test_regexp_invalid(self, pattern: str, invalid_values: list[str]) -> None:
        validator = mr.regexp_validate(pattern)
        for value in invalid_values:
            with pytest.raises(marshmallow.ValidationError):
                validator(value)

    def test_validate_with_various_predicates(self) -> None:
        # Test positive numbers
        positive_validator = mr.validate(lambda x: x > 0, error="Must be positive")
        positive_validator(1)
        positive_validator(0.001)
        positive_validator(9999999999)
        with pytest.raises(marshmallow.ValidationError):
            positive_validator(0)
        with pytest.raises(marshmallow.ValidationError):
            positive_validator(-1)

    def test_validate_string_length(self) -> None:
        length_validator = mr.validate(lambda x: 1 <= len(x) <= 100, error="Length must be 1-100")
        length_validator("a")
        length_validator("x" * 100)
        with pytest.raises(marshmallow.ValidationError):
            length_validator("")
        with pytest.raises(marshmallow.ValidationError):
            length_validator("x" * 101)

    def test_validate_range(self) -> None:
        range_validator = mr.validate(lambda x: 0 <= x <= 100, error="Must be 0-100")
        range_validator(0)
        range_validator(50)
        range_validator(100)
        with pytest.raises(marshmallow.ValidationError):
            range_validator(-1)
        with pytest.raises(marshmallow.ValidationError):
            range_validator(101)

    def test_email_unicode_domain_accepted(self) -> None:
        validator = mr.email_validate()
        # Marshmallow's email validator accepts unicode domains via IDNA encoding
        validator("user@домен.рф")

    def test_regexp_unicode_pattern(self) -> None:
        validator = mr.regexp_validate(r"^[\u0400-\u04FF]+$")  # Cyrillic
        validator("Привет")
        with pytest.raises(marshmallow.ValidationError):
            validator("Hello")

    def test_validation_error_multiple_fields(self) -> None:
        error = marshmallow.ValidationError({"field1": ["Error 1"], "field2": ["Error 2"], "field3": ["Error 3"]})
        result = mr.get_validation_field_errors(error)
        assert len(result) == 3

    def test_validation_error_deeply_nested(self) -> None:
        error = marshmallow.ValidationError({"level1": {"level2": {"level3": ["Deep error"]}}})
        result = mr.get_validation_field_errors(error)
        assert len(result) == 1
        assert result[0].name == "level1"
        assert result[0].nested_errors is not None
        assert result[0].nested_errors[0].name == "level2"
