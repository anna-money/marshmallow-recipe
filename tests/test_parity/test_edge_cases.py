from typing import Any

from tests.test_parity.conftest import ForEdgeCases


def test_unicode_cyrillic(impl: Any) -> None:
    obj = ForEdgeCases(text="Привет мир", number=1, small_float=1.0)
    result = impl.dump(ForEdgeCases, obj)
    loaded = impl.load(ForEdgeCases, result.encode() if isinstance(result, str) else result)
    assert loaded.text == "Привет мир"


def test_unicode_chinese(impl: Any) -> None:
    obj = ForEdgeCases(text="你好世界", number=2, small_float=1.0)
    result = impl.dump(ForEdgeCases, obj)
    loaded = impl.load(ForEdgeCases, result.encode() if isinstance(result, str) else result)
    assert loaded.text == "你好世界"


def test_emoji(impl: Any) -> None:
    obj = ForEdgeCases(text="Hello 👋 World 🌍", number=3, small_float=1.0)
    result = impl.dump(ForEdgeCases, obj)
    loaded = impl.load(ForEdgeCases, result.encode() if isinstance(result, str) else result)
    assert loaded.text == "Hello 👋 World 🌍"


def test_empty_string(impl: Any) -> None:
    obj = ForEdgeCases(text="", number=4, small_float=1.0)
    result = impl.dump(ForEdgeCases, obj)
    assert result == '{"number": 4, "small_float": 1.0, "text": ""}'


def test_whitespace_string(impl: Any) -> None:
    obj = ForEdgeCases(text="  spaces  ", number=5, small_float=1.0)
    result = impl.dump(ForEdgeCases, obj)
    assert result == '{"number": 5, "small_float": 1.0, "text": "  spaces  "}'


def test_special_chars(impl: Any) -> None:
    obj = ForEdgeCases(text="Line1\nLine2\tTab\r\nNewline\"Quote'", number=6, small_float=1.0)
    dumped = impl.dump(ForEdgeCases, obj)
    loaded = impl.load(ForEdgeCases, dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded.text == "Line1\nLine2\tTab\r\nNewline\"Quote'"


def test_very_large_int(impl: Any) -> None:
    obj = ForEdgeCases(text="x", number=9223372036854775807, small_float=1.0)
    result = impl.dump(ForEdgeCases, obj)
    loaded = impl.load(ForEdgeCases, result.encode() if isinstance(result, str) else result)
    assert loaded.number == 9223372036854775807


def test_very_small_float(impl: Any) -> None:
    obj = ForEdgeCases(text="x", number=1, small_float=1e-100)
    dumped = impl.dump(ForEdgeCases, obj)
    loaded = impl.load(ForEdgeCases, dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded.small_float == 1e-100


def test_negative_zero_float(impl: Any) -> None:
    obj = ForEdgeCases(text="x", number=1, small_float=-0.0)
    dumped = impl.dump(ForEdgeCases, obj)
    loaded = impl.load(ForEdgeCases, dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded.small_float == 0.0
