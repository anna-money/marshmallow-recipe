import dataclasses

import pytest

import marshmallow_recipe as mr

from .conftest import Serializer, SimpleTypes, WithCustomName


class TestUnknownFieldsDump:
    def test_only_defined_fields(self, impl: Serializer) -> None:
        obj = SimpleTypes(name="Bob", age=35)
        result = impl.dump(SimpleTypes, obj)
        assert result == b'{"name":"Bob","age":35}'


class TestUnknownFieldsLoad:
    def test_ignored_in_load(self, impl: Serializer) -> None:
        data = b'{"name":"test","age":30,"extra_field":"should_be_ignored"}'
        result = impl.load(SimpleTypes, data)
        assert result == SimpleTypes(name="test", age=30)

    def test_multiple_ignored(self, impl: Serializer) -> None:
        data = b'{"name":"Alice","age":25,"email":"ignored","phone":"ignored","address":"ignored"}'
        result = impl.load(SimpleTypes, data)
        assert result == SimpleTypes(name="Alice", age=25)

    def test_custom_name_with_extra_fields(self, impl: Serializer) -> None:
        data = b'{"id":123,"email":"test@example.com","extra":"ignored"}'
        result = impl.load(WithCustomName, data)
        assert result == WithCustomName(internal_id=123, user_email="test@example.com")

    def test_original_field_name_ignored_when_renamed(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithRenamedField:
            field_1: str = dataclasses.field(metadata=mr.meta(name="field_2"))

        data = b'{"field_1":"bad","field_2":"good"}'
        result = impl.load(WithRenamedField, data)
        assert result == WithRenamedField(field_1="good")

    def test_metadata_name_cannot_conflict_with_other_field(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithConflictingName:
            field_1: str = dataclasses.field(metadata=mr.meta(name="field_2"))
            field_2: str

        with pytest.raises(ValueError) as exc:
            impl.load(WithConflictingName, b'{"field_1":"bad","field_2":"good"}')
        assert exc.value.args[0] == "Invalid name=field_2 in metadata for field=field_1"
