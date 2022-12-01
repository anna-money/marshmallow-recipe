import dataclasses

import pytest

import marshmallow_recipe as mr


def test_unknown_fields_should_be_excluded() -> None:
    @dataclasses.dataclass
    class Example:
        field_1: str = dataclasses.field(metadata=mr.metadata(name="field_2"))

    expected = mr.load(Example, {"field_1": "bad", "field_2": "good"})
    assert expected == Example(field_1="good")


def test_metadata_name_should_not_use_others_field_name() -> None:
    @dataclasses.dataclass
    class Example:
        field_1: str = dataclasses.field(metadata=mr.metadata(name="field_2"))
        field_2: str

    with pytest.raises(ValueError) as e:
        mr.load(Example, {"field_1": "bad", "field_2": "good"})

    assert e.value.args[0] == "Invalid name=field_2 in metadata for field=field_1"
