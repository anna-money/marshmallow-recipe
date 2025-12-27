from typing import Any

from tests.test_parity.conftest import WithPostLoadAndStrip, WithPostLoadTransform


def test_post_load_transform_dump(impl: Any) -> None:
    obj = WithPostLoadTransform(name="hello")
    result = impl.dump(WithPostLoadTransform, obj)
    assert result == '{"name": "hello"}'


def test_post_load_transform_load(impl: Any) -> None:
    data = b'{"name": "hello"}'
    result = impl.load(WithPostLoadTransform, data)
    assert result == WithPostLoadTransform(name="HELLO")


def test_post_load_with_strip_dump(impl: Any) -> None:
    obj = WithPostLoadAndStrip(value="WORLD")
    result = impl.dump(WithPostLoadAndStrip, obj)
    assert result == '{"value": "WORLD"}'


def test_post_load_with_strip_load(impl: Any) -> None:
    data = b'{"value": "  HELLO  "}'
    result = impl.load(WithPostLoadAndStrip, data)
    assert result == WithPostLoadAndStrip(value="hello")


def test_post_load_roundtrip(impl: Any) -> None:
    data = b'{"name": "test"}'
    loaded = impl.load(WithPostLoadTransform, data)
    assert loaded == WithPostLoadTransform(name="TEST")
    dumped = impl.dump(WithPostLoadTransform, loaded)
    assert dumped == '{"name": "TEST"}'
