import dataclasses

import marshmallow_recipe as mr


def test_unknown_fields_should_be_excluded() -> None:
    @dataclasses.dataclass
    class Example:
        field_1: str = dataclasses.field(metadata=mr.metadata(name="field_2"))

    expected = mr.load(Example, {"field_1": "bad", "field_2": "good"})
    assert expected == Example(field_1="good")
