import dataclasses
import enum
from typing import Literal

import marshmallow
import pytest

from .conftest import (
    IntDiscriminator,
    Priority,
    Serializer,
    Status,
    StrDiscriminator,
    WithBoolLiteral,
    WithBoolLiteralDefault,
    WithBoolLiteralInvalidError,
    WithBoolLiteralMissing,
    WithBoolLiteralNoneError,
    WithBoolLiteralRequiredError,
    WithBoolLiteralTrue,
    WithIntEnumLiteral,
    WithIntEnumLiteralDefault,
    WithIntEnumLiteralInvalidError,
    WithIntEnumLiteralMissing,
    WithIntEnumLiteralNoneError,
    WithIntEnumLiteralRequiredError,
    WithIntEnumLiteralSingle,
    WithIntLiteral,
    WithIntLiteralDefault,
    WithIntLiteralInvalidError,
    WithIntLiteralMissing,
    WithIntLiteralNoneError,
    WithIntLiteralRequiredError,
    WithLegacyIntEnumLiteral,
    WithLegacyStrEnumLiteral,
    WithOptionalBoolLiteral,
    WithOptionalIntEnumLiteral,
    WithOptionalIntLiteral,
    WithOptionalStrEnumLiteral,
    WithOptionalStrLiteral,
    WithStrEnumLiteral,
    WithStrEnumLiteralDefault,
    WithStrEnumLiteralInvalidError,
    WithStrEnumLiteralMissing,
    WithStrEnumLiteralNoneError,
    WithStrEnumLiteralRequiredError,
    WithStrEnumLiteralSingle,
    WithStrLiteral,
    WithStrLiteralDefault,
    WithStrLiteralInvalidError,
    WithStrLiteralMissing,
    WithStrLiteralNoneError,
    WithStrLiteralRequiredError,
)


class TestStrLiteralDump:
    def test_value(self, impl: Serializer) -> None:
        obj = WithStrLiteral(value="a")
        result = impl.dump(WithStrLiteral, obj)
        assert result == b'{"value":"a"}'

    def test_other_value(self, impl: Serializer) -> None:
        obj = WithStrLiteral(value="c")
        result = impl.dump(WithStrLiteral, obj)
        assert result == b'{"value":"c"}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = WithOptionalStrLiteral(value=None)
        result = impl.dump(WithOptionalStrLiteral, obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = WithOptionalStrLiteral(value="x")
        result = impl.dump(WithOptionalStrLiteral, obj)
        assert result == b'{"value":"x"}'

    def test_default(self, impl: Serializer) -> None:
        obj = WithStrLiteralDefault()
        result = impl.dump(WithStrLiteralDefault, obj)
        assert result == b'{"value":"a"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithStrLiteralMissing()
        result = impl.dump(WithStrLiteralMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithStrLiteralMissing(value="b")
        result = impl.dump(WithStrLiteralMissing, obj)
        assert result == b'{"value":"b"}'

    def test_invalid_type(self, impl: Serializer) -> None:
        obj = WithStrLiteral(**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithStrLiteral, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['a', 'b', 'c']"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithStrLiteralInvalidError(**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithStrLiteralInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestIntLiteralDump:
    def test_value(self, impl: Serializer) -> None:
        obj = WithIntLiteral(value=1)
        result = impl.dump(WithIntLiteral, obj)
        assert result == b'{"value":1}'

    def test_other_value(self, impl: Serializer) -> None:
        obj = WithIntLiteral(value=3)
        result = impl.dump(WithIntLiteral, obj)
        assert result == b'{"value":3}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = WithOptionalIntLiteral(value=None)
        result = impl.dump(WithOptionalIntLiteral, obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = WithOptionalIntLiteral(value=2)
        result = impl.dump(WithOptionalIntLiteral, obj)
        assert result == b'{"value":2}'

    def test_default(self, impl: Serializer) -> None:
        obj = WithIntLiteralDefault()
        result = impl.dump(WithIntLiteralDefault, obj)
        assert result == b'{"value":1}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithIntLiteralMissing()
        result = impl.dump(WithIntLiteralMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithIntLiteralMissing(value=2)
        result = impl.dump(WithIntLiteralMissing, obj)
        assert result == b'{"value":2}'

    def test_invalid_type(self, impl: Serializer) -> None:
        obj = WithIntLiteral(**{"value": "not an int"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithIntLiteral, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_invalid_type_bool(self, impl: Serializer) -> None:
        obj = WithIntLiteral(**{"value": True})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithIntLiteral, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithIntLiteralInvalidError(**{"value": "not an int"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithIntLiteralInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestBoolLiteralDump:
    def test_true(self, impl: Serializer) -> None:
        obj = WithBoolLiteral(value=True)
        result = impl.dump(WithBoolLiteral, obj)
        assert result == b'{"value":true}'

    def test_false(self, impl: Serializer) -> None:
        obj = WithBoolLiteral(value=False)
        result = impl.dump(WithBoolLiteral, obj)
        assert result == b'{"value":false}'

    def test_true_only(self, impl: Serializer) -> None:
        obj = WithBoolLiteralTrue(value=True)
        result = impl.dump(WithBoolLiteralTrue, obj)
        assert result == b'{"value":true}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = WithOptionalBoolLiteral(value=None)
        result = impl.dump(WithOptionalBoolLiteral, obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = WithOptionalBoolLiteral(value=True)
        result = impl.dump(WithOptionalBoolLiteral, obj)
        assert result == b'{"value":true}'

    def test_default(self, impl: Serializer) -> None:
        obj = WithBoolLiteralDefault()
        result = impl.dump(WithBoolLiteralDefault, obj)
        assert result == b'{"value":true}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithBoolLiteralMissing()
        result = impl.dump(WithBoolLiteralMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithBoolLiteralMissing(value=False)
        result = impl.dump(WithBoolLiteralMissing, obj)
        assert result == b'{"value":false}'

    def test_invalid_type(self, impl: Serializer) -> None:
        obj = WithBoolLiteral(**{"value": 1})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithBoolLiteral, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [True, False]"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithBoolLiteralInvalidError(**{"value": 1})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithBoolLiteralInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestStrLiteralLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"b"}'
        result = impl.load(WithStrLiteral, data)
        assert result == WithStrLiteral(value="b")

    def test_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteral, data)
        assert exc.value.messages == {"value": ["Field may not be null."]}

    def test_optional_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(WithOptionalStrLiteral, data)
        assert result == WithOptionalStrLiteral(value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"y"}'
        result = impl.load(WithOptionalStrLiteral, data)
        assert result == WithOptionalStrLiteral(value="y")

    def test_optional_missing_key(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalStrLiteral, data)
        assert result == WithOptionalStrLiteral(value=None)

    def test_default(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrLiteralDefault, data)
        assert result == WithStrLiteralDefault(value="a")

    def test_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":"z"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['a', 'b', 'c']"]}

    def test_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['a', 'b', 'c']"]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteral, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrLiteralMissing, data)
        assert result == WithStrLiteralMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"a"}'
        result = impl.load(WithStrLiteralMissing, data)
        assert result == WithStrLiteralMissing(value="a")

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteralRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteralNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"z"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrLiteralInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestIntLiteralLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":2}'
        result = impl.load(WithIntLiteral, data)
        assert result == WithIntLiteral(value=2)

    def test_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Field may not be null."]}

    def test_optional_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(WithOptionalIntLiteral, data)
        assert result == WithOptionalIntLiteral(value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":3}'
        result = impl.load(WithOptionalIntLiteral, data)
        assert result == WithOptionalIntLiteral(value=3)

    def test_optional_missing_key(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalIntLiteral, data)
        assert result == WithOptionalIntLiteral(value=None)

    def test_default(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithIntLiteralDefault, data)
        assert result == WithIntLiteralDefault(value=1)

    def test_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":999}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":"not_a_number"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_bool_rejected(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2, 3]"]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteral, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithIntLiteralMissing, data)
        assert result == WithIntLiteralMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        result = impl.load(WithIntLiteralMissing, data)
        assert result == WithIntLiteralMissing(value=1)

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteralRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteralNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":999}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntLiteralInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestBoolLiteralLoad:
    def test_true(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolLiteral, data)
        assert result == WithBoolLiteral(value=True)

    def test_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteral, data)
        assert exc.value.messages == {"value": ["Field may not be null."]}

    def test_false(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        result = impl.load(WithBoolLiteral, data)
        assert result == WithBoolLiteral(value=False)

    def test_true_only_valid(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolLiteralTrue, data)
        assert result == WithBoolLiteralTrue(value=True)

    def test_true_only_invalid(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteralTrue, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [True]"]}

    def test_optional_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(WithOptionalBoolLiteral, data)
        assert result == WithOptionalBoolLiteral(value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        result = impl.load(WithOptionalBoolLiteral, data)
        assert result == WithOptionalBoolLiteral(value=False)

    def test_optional_missing_key(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalBoolLiteral, data)
        assert result == WithOptionalBoolLiteral(value=None)

    def test_default(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithBoolLiteralDefault, data)
        assert result == WithBoolLiteralDefault(value=True)

    def test_wrong_type_int(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [True, False]"]}

    def test_wrong_type_str(self, impl: Serializer) -> None:
        data = b'{"value":"true"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [True, False]"]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteral, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithBoolLiteralMissing, data)
        assert result == WithBoolLiteralMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolLiteralMissing, data)
        assert result == WithBoolLiteralMissing(value=True)

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteralRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteralNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolLiteralInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestUnsupportedLiterals:
    def test_literal_with_none_value(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithLiteralNone:
            value: Literal["a", "b", None]

        with pytest.raises(ValueError, match="Unsupported Literal values"):
            impl.dump(WithLiteralNone, WithLiteralNone(value="a"))

    def test_literal_with_mixed_types(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithMixedLiteral:
            value: Literal[1, "hello"]

        with pytest.raises(ValueError, match="Unsupported Literal values"):
            impl.dump(WithMixedLiteral, WithMixedLiteral(value=1))

    def test_literal_with_bytes(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithBytesLiteral:
            value: Literal[b"hello"]

        with pytest.raises(ValueError, match="Unsupported Literal values"):
            impl.dump(WithBytesLiteral, WithBytesLiteral(value=b"hello"))

    def test_literal_with_mixed_enum_classes(self, impl: Serializer) -> None:
        class A(enum.StrEnum):
            X = "X"

        class B(enum.StrEnum):
            Y = "Y"

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithMixedEnumLiteral:
            value: Literal[A.X, B.Y]

        with pytest.raises(ValueError, match="Unsupported Literal values"):
            impl.dump(WithMixedEnumLiteral, WithMixedEnumLiteral(value=A.X))

    def test_literal_with_enum_and_raw_str(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithMixedLiteral:
            value: Literal[StrDiscriminator.DOG, "raw"]

        with pytest.raises(ValueError, match="Unsupported Literal values"):
            impl.dump(WithMixedLiteral, WithMixedLiteral(value=StrDiscriminator.DOG))


class TestStrEnumLiteralDump:
    def test_value(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteral(value=StrDiscriminator.DOG)
        result = impl.dump(WithStrEnumLiteral, obj)
        assert result == b'{"value":"DOG"}'

    def test_other_value(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteral(value=StrDiscriminator.CAT)
        result = impl.dump(WithStrEnumLiteral, obj)
        assert result == b'{"value":"CAT"}'

    def test_single_value(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteralSingle(value=StrDiscriminator.DOG)
        result = impl.dump(WithStrEnumLiteralSingle, obj)
        assert result == b'{"value":"DOG"}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = WithOptionalStrEnumLiteral(value=None)
        result = impl.dump(WithOptionalStrEnumLiteral, obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = WithOptionalStrEnumLiteral(value=StrDiscriminator.DOG)
        result = impl.dump(WithOptionalStrEnumLiteral, obj)
        assert result == b'{"value":"DOG"}'

    def test_default(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteralDefault()
        result = impl.dump(WithStrEnumLiteralDefault, obj)
        assert result == b'{"value":"DOG"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteralMissing()
        result = impl.dump(WithStrEnumLiteralMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteralMissing(value=StrDiscriminator.CAT)
        result = impl.dump(WithStrEnumLiteralMissing, obj)
        assert result == b'{"value":"CAT"}'

    def test_subset_violation(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteralSingle(**{"value": StrDiscriminator.CAT})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithStrEnumLiteralSingle, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['DOG']"]}

    def test_invalid_type(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteral(**{"value": "DOG"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithStrEnumLiteral, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['DOG', 'CAT']"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithStrEnumLiteralInvalidError(**{"value": StrDiscriminator.BIRD})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithStrEnumLiteralInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestStrEnumLiteralLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"CAT"}'
        result = impl.load(WithStrEnumLiteral, data)
        assert result == WithStrEnumLiteral(value=StrDiscriminator.CAT)
        assert result.value is StrDiscriminator.CAT

    def test_other_value(self, impl: Serializer) -> None:
        data = b'{"value":"DOG"}'
        result = impl.load(WithStrEnumLiteral, data)
        assert result == WithStrEnumLiteral(value=StrDiscriminator.DOG)
        assert result.value is StrDiscriminator.DOG

    def test_single_value(self, impl: Serializer) -> None:
        data = b'{"value":"DOG"}'
        result = impl.load(WithStrEnumLiteralSingle, data)
        assert result == WithStrEnumLiteralSingle(value=StrDiscriminator.DOG)
        assert result.value is StrDiscriminator.DOG

    def test_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteral, data)
        assert exc.value.messages == {"value": ["Field may not be null."]}

    def test_optional_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(WithOptionalStrEnumLiteral, data)
        assert result == WithOptionalStrEnumLiteral(value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"CAT"}'
        result = impl.load(WithOptionalStrEnumLiteral, data)
        assert result == WithOptionalStrEnumLiteral(value=StrDiscriminator.CAT)
        assert result.value is StrDiscriminator.CAT

    def test_optional_missing_key(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalStrEnumLiteral, data)
        assert result == WithOptionalStrEnumLiteral(value=None)

    def test_default(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrEnumLiteralDefault, data)
        assert result == WithStrEnumLiteralDefault(value=StrDiscriminator.DOG)
        assert result.value is StrDiscriminator.DOG

    def test_subset_violation(self, impl: Serializer) -> None:
        data = b'{"value":"BIRD"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['DOG', 'CAT']"]}

    def test_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":"WOLF"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['DOG', 'CAT']"]}

    def test_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['DOG', 'CAT']"]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteral, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrEnumLiteralMissing, data)
        assert result == WithStrEnumLiteralMissing()

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteralRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteralNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"BIRD"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumLiteralInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestIntEnumLiteralDump:
    def test_value(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteral(value=IntDiscriminator.ONE)
        result = impl.dump(WithIntEnumLiteral, obj)
        assert result == b'{"value":1}'

    def test_other_value(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteral(value=IntDiscriminator.TWO)
        result = impl.dump(WithIntEnumLiteral, obj)
        assert result == b'{"value":2}'

    def test_single_value(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteralSingle(value=IntDiscriminator.ONE)
        result = impl.dump(WithIntEnumLiteralSingle, obj)
        assert result == b'{"value":1}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = WithOptionalIntEnumLiteral(value=None)
        result = impl.dump(WithOptionalIntEnumLiteral, obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = WithOptionalIntEnumLiteral(value=IntDiscriminator.ONE)
        result = impl.dump(WithOptionalIntEnumLiteral, obj)
        assert result == b'{"value":1}'

    def test_default(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteralDefault()
        result = impl.dump(WithIntEnumLiteralDefault, obj)
        assert result == b'{"value":1}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteralMissing()
        result = impl.dump(WithIntEnumLiteralMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteralMissing(value=IntDiscriminator.TWO)
        result = impl.dump(WithIntEnumLiteralMissing, obj)
        assert result == b'{"value":2}'

    def test_subset_violation(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteralSingle(**{"value": IntDiscriminator.TWO})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithIntEnumLiteralSingle, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1]"]}

    def test_invalid_type(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteral(**{"value": 1})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithIntEnumLiteral, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2]"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithIntEnumLiteralInvalidError(**{"value": IntDiscriminator.THREE})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithIntEnumLiteralInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestIntEnumLiteralLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        result = impl.load(WithIntEnumLiteral, data)
        assert result == WithIntEnumLiteral(value=IntDiscriminator.ONE)
        assert result.value is IntDiscriminator.ONE

    def test_other_value(self, impl: Serializer) -> None:
        data = b'{"value":2}'
        result = impl.load(WithIntEnumLiteral, data)
        assert result == WithIntEnumLiteral(value=IntDiscriminator.TWO)
        assert result.value is IntDiscriminator.TWO

    def test_single_value(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        result = impl.load(WithIntEnumLiteralSingle, data)
        assert result == WithIntEnumLiteralSingle(value=IntDiscriminator.ONE)
        assert result.value is IntDiscriminator.ONE

    def test_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteral, data)
        assert exc.value.messages == {"value": ["Field may not be null."]}

    def test_optional_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(WithOptionalIntEnumLiteral, data)
        assert result == WithOptionalIntEnumLiteral(value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":2}'
        result = impl.load(WithOptionalIntEnumLiteral, data)
        assert result == WithOptionalIntEnumLiteral(value=IntDiscriminator.TWO)
        assert result.value is IntDiscriminator.TWO

    def test_optional_missing_key(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalIntEnumLiteral, data)
        assert result == WithOptionalIntEnumLiteral(value=None)

    def test_default(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithIntEnumLiteralDefault, data)
        assert result == WithIntEnumLiteralDefault(value=IntDiscriminator.ONE)
        assert result.value is IntDiscriminator.ONE

    def test_subset_violation(self, impl: Serializer) -> None:
        data = b'{"value":3}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2]"]}

    def test_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":99}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2]"]}

    def test_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":"not an int"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 2]"]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteral, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithIntEnumLiteralMissing, data)
        assert result == WithIntEnumLiteralMissing()

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteralRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteralNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":99}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumLiteralInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestLegacyStrEnumLiteralDump:
    def test_value(self, impl: Serializer) -> None:
        obj = WithLegacyStrEnumLiteral(value=Status.INACTIVE)
        result = impl.dump(WithLegacyStrEnumLiteral, obj)
        assert result == b'{"value":"inactive"}'


class TestLegacyStrEnumLiteralLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"active"}'
        result = impl.load(WithLegacyStrEnumLiteral, data)
        assert result == WithLegacyStrEnumLiteral(value=Status.ACTIVE)
        assert result.value is Status.ACTIVE

    def test_subset_violation(self, impl: Serializer) -> None:
        data = b'{"value":"pending"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithLegacyStrEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: ['active', 'inactive']"]}


class TestLegacyIntEnumLiteralDump:
    def test_value(self, impl: Serializer) -> None:
        obj = WithLegacyIntEnumLiteral(value=Priority.HIGH)
        result = impl.dump(WithLegacyIntEnumLiteral, obj)
        assert result == b'{"value":3}'


class TestLegacyIntEnumLiteralLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        result = impl.load(WithLegacyIntEnumLiteral, data)
        assert result == WithLegacyIntEnumLiteral(value=Priority.LOW)
        assert result.value is Priority.LOW

    def test_subset_violation(self, impl: Serializer) -> None:
        data = b'{"value":2}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithLegacyIntEnumLiteral, data)
        assert exc.value.messages == {"value": ["Not a valid value. Allowed values: [1, 3]"]}
