import copy
import dataclasses

import pytest

import marshmallow_recipe as mr


def test_unknown_fields_should_be_excluded() -> None:
    @dataclasses.dataclass
    class Example:
        field_1: str = dataclasses.field(metadata=mr.meta(name="field_2"))

    data = {"field_1": "bad", "field_2": "good"}
    data_copy = copy.deepcopy(data)
    expected = mr.load(Example, data_copy)
    assert expected == Example(field_1="good")
    assert data == data_copy


def test_metadata_name_should_not_use_others_field_name() -> None:
    @dataclasses.dataclass
    class Example:
        field_1: str = dataclasses.field(metadata=mr.meta(name="field_2"))
        field_2: str

    with pytest.raises(ValueError) as e:
        mr.load(Example, {"field_1": "bad", "field_2": "good"})

    assert e.value.args[0] == "Invalid name=field_2 in metadata for field=field_1"
