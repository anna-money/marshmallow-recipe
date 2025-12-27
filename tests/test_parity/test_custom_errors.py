from typing import Any

import marshmallow
import pytest

from tests.test_parity.conftest import WithCustomInvalidError, WithCustomNoneError, WithCustomRequiredError


def test_custom_required_error(impl: Any) -> None:
    data = b"{}"
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(WithCustomRequiredError, data)
    assert exc.value.messages == {"name": ["Custom required message"]}


def test_custom_invalid_error_wrong_type(impl: Any) -> None:
    data = b'{"age": "not-a-number"}'
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(WithCustomInvalidError, data)
    assert exc.value.messages == {"age": ["Custom invalid message"]}


def test_custom_none_error(impl: Any) -> None:
    data = b'{"value": null}'
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(WithCustomNoneError, data)
    assert exc.value.messages == {"value": ["Custom none message"]}


def test_default_errors_still_work(impl: Any) -> None:
    data = b'{"name": "test", "age": 25}'
    result = impl.load(WithCustomInvalidError, data)
    assert result == WithCustomInvalidError(age=25)
