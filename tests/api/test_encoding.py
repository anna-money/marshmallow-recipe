from .conftest import Serializer, ValueOf


class TestAsciiSafeEncoding:
    def test_cyrillic_escaped_to_ascii(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="Привет")
        assert impl.dump(ValueOf[str], obj) == b'{"value":"\\u041f\\u0440\\u0438\\u0432\\u0435\\u0442"}'

    def test_emoji_escaped_to_ascii(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="👋")
        assert impl.dump(ValueOf[str], obj) == b'{"value":"\\ud83d\\udc4b"}'

    def test_chinese_escaped_to_ascii(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="你好")
        assert impl.dump(ValueOf[str], obj) == b'{"value":"\\u4f60\\u597d"}'

    def test_ascii_not_escaped(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="hello")
        assert impl.dump(ValueOf[str], obj) == b'{"value":"hello"}'
