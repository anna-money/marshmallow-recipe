import json

import pytest

from .conftest import (
    AssistantMsg,
    Msg,
    Serializer,
    UserMsg,
    WithChainedTypeAlias,
    WithIntTypeAlias,
    WithOptionalStrTypeAlias,
    WithStrTypeAlias,
    WithUnionTypeAlias,
)


class TestTypeAliasDump:
    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(WithStrTypeAlias(value="hello"), b'{"value":"hello"}', id="str"),
            pytest.param(WithChainedTypeAlias(value="hello"), b'{"value":"hello"}', id="chained_str"),
            pytest.param(WithIntTypeAlias(value=42), b'{"value":42}', id="int"),
        ],
    )
    def test_simple_alias(self, impl: Serializer, obj: object, expected: bytes) -> None:
        result = impl.dump(type(obj), obj)
        assert result == expected

    def test_optional_str_alias_none(self, impl: Serializer) -> None:
        obj = WithOptionalStrTypeAlias(value=None)
        result = impl.dump(WithOptionalStrTypeAlias, obj)
        assert result == b"{}"

    def test_optional_str_alias_value(self, impl: Serializer) -> None:
        obj = WithOptionalStrTypeAlias(value="hello")
        result = impl.dump(WithOptionalStrTypeAlias, obj)
        assert result == b'{"value":"hello"}'

    def test_union_alias_str(self, impl: Serializer) -> None:
        obj = WithUnionTypeAlias(value="hello")
        result = impl.dump(WithUnionTypeAlias, obj)
        assert result == b'{"value":"hello"}'

    def test_union_alias_int(self, impl: Serializer) -> None:
        obj = WithUnionTypeAlias(value=42)
        result = impl.dump(WithUnionTypeAlias, obj)
        assert result == b'{"value":42}'

    def test_discriminated_union_user(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")
        obj = UserMsg(text="hi")
        result = json.loads(impl.dump(Msg, obj))  # type: ignore[arg-type]
        assert result == {"role": "user", "text": "hi"}

    def test_discriminated_union_assistant(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")
        obj = AssistantMsg(text="hello")
        result = json.loads(impl.dump(Msg, obj))  # type: ignore[arg-type]
        assert result == {"role": "assistant", "text": "hello"}

    def test_discriminated_union_dump_many(self, impl: Serializer) -> None:
        if not impl.supports_many:
            pytest.skip("does not support many")
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")
        messages = [UserMsg(text="hi"), AssistantMsg(text="hello")]
        result = json.loads(impl.dump_many(Msg, messages))  # type: ignore[arg-type]
        assert result == [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}]


class TestTypeAliasLoad:
    @pytest.mark.parametrize(
        ("cls", "data", "expected"),
        [
            pytest.param(WithStrTypeAlias, b'{"value":"hello"}', WithStrTypeAlias(value="hello"), id="str"),
            pytest.param(
                WithChainedTypeAlias, b'{"value":"hello"}', WithChainedTypeAlias(value="hello"), id="chained_str"
            ),
            pytest.param(WithIntTypeAlias, b'{"value":42}', WithIntTypeAlias(value=42), id="int"),
        ],
    )
    def test_simple_alias(self, impl: Serializer, cls: type, data: bytes, expected: object) -> None:
        result = impl.load(cls, data)
        assert result == expected

    def test_optional_str_alias_null(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(WithOptionalStrTypeAlias, data)
        assert result == WithOptionalStrTypeAlias(value=None)

    def test_optional_str_alias_value(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithOptionalStrTypeAlias, data)
        assert result == WithOptionalStrTypeAlias(value="hello")

    def test_optional_str_alias_missing_key(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalStrTypeAlias, data)
        assert result == WithOptionalStrTypeAlias(value=None)

    def test_union_alias_str(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithUnionTypeAlias, data)
        assert result == WithUnionTypeAlias(value="hello")

    def test_union_alias_int(self, impl: Serializer) -> None:
        data = b'{"value":42}'
        result = impl.load(WithUnionTypeAlias, data)
        assert result == WithUnionTypeAlias(value=42)

    def test_discriminated_union_user(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")
        data = b'{"text":"hi","role":"user"}'
        result = impl.load(Msg, data)  # type: ignore[arg-type]
        assert result == UserMsg(text="hi", role="user")

    def test_discriminated_union_assistant(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")
        data = b'{"text":"hello","role":"assistant"}'
        result = impl.load(Msg, data)  # type: ignore[arg-type]
        assert result == AssistantMsg(text="hello", role="assistant")

    def test_discriminated_union_invalid_role(self, impl: Serializer) -> None:
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")
        data = b'{"text":"hi","role":"unknown"}'
        with pytest.raises(Exception):
            impl.load(Msg, data)

    def test_discriminated_union_load_many(self, impl: Serializer) -> None:
        if not impl.supports_many:
            pytest.skip("does not support many")
        if not impl.supports_root_type_alias_union:
            pytest.skip("does not support root type alias union")
        data = b'[{"text":"hi","role":"user"},{"text":"hello","role":"assistant"}]'
        result = impl.load_many(Msg, data)  # type: ignore[arg-type]
        assert result == [UserMsg(text="hi", role="user"), AssistantMsg(text="hello", role="assistant")]
