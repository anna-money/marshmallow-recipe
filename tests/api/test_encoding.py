import pytest

from .conftest import Serializer, ValueOf


class TestEncodingDump:
    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(
                ValueOf[str](value="Привет"), b'{"value":"\\u041f\\u0440\\u0438\\u0432\\u0435\\u0442"}', id="cyrillic"
            ),
            pytest.param(ValueOf[str](value="👋"), b'{"value":"\\ud83d\\udc4b"}', id="emoji"),
            pytest.param(ValueOf[str](value="你好"), b'{"value":"\\u4f60\\u597d"}', id="chinese"),
            pytest.param(ValueOf[str](value="hello"), b'{"value":"hello"}', id="ascii"),
        ],
    )
    def test_non_ascii_escaped(self, impl: Serializer, obj: ValueOf[str], expected: bytes) -> None:
        assert impl.dump(ValueOf[str], obj) == expected


class TestEncodingLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"\\u0041"}', "A", id="ascii"),
            pytest.param(b'{"value":"\\u0410"}', "А", id="cyrillic"),  # noqa: RUF001
            pytest.param(b'{"value":"\\u4e2d"}', "中", id="chinese"),
            pytest.param(b'{"value":"\\ud83d\\ude00"}', "😀", id="emoji_surrogate_pair"),
            pytest.param(b'{"value":"Hello \\u0041\\u0042\\u0043"}', "Hello ABC", id="mixed"),
        ],
    )
    def test_unicode_escape(self, impl: Serializer, data: bytes, expected: str) -> None:
        result = impl.load(ValueOf[str], data)
        assert result == ValueOf[str](value=expected)
