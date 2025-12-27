from typing import Any

import marshmallow
import pytest

from tests.test_parity.conftest import WithListItemValidation, WithSetItemValidation, WithTupleItemValidation


def test_list_item_validation_pass(impl: Any) -> None:
    data = b'{"items": [1, 2, 3]}'
    result = impl.load(WithListItemValidation, data)
    assert result == WithListItemValidation(items=[1, 2, 3])


def test_list_item_validation_fail(impl: Any) -> None:
    data = b'{"items": [1, 0, 3]}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithListItemValidation, data)


def test_list_item_validation_negative_fail(impl: Any) -> None:
    data = b'{"items": [1, -5, 3]}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithListItemValidation, data)


def test_set_item_validation_pass(impl: Any) -> None:
    data = b'{"tags": ["a", "b", "c"]}'
    result = impl.load(WithSetItemValidation, data)
    assert result == WithSetItemValidation(tags={"a", "b", "c"})


def test_set_item_validation_fail(impl: Any) -> None:
    data = b'{"tags": ["a", "", "c"]}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithSetItemValidation, data)


def test_tuple_item_validation_pass(impl: Any) -> None:
    data = b'{"values": [1, 2, 3]}'
    result = impl.load(WithTupleItemValidation, data)
    assert result == WithTupleItemValidation(values=(1, 2, 3))


def test_tuple_item_validation_fail(impl: Any) -> None:
    data = b'{"values": [1, 0, 3]}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithTupleItemValidation, data)


def test_list_item_validation_dump(impl: Any) -> None:
    obj = WithListItemValidation(items=[5, 10, 15])
    result = impl.dump(WithListItemValidation, obj)
    assert result == '{"items": [5, 10, 15]}'
