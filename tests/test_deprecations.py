import dataclasses
import warnings

import pytest

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SimpleData:
    value: str


class TestLoadNoneValueHandlingDeprecation:
    def test_load_warns(self) -> None:
        with pytest.warns(DeprecationWarning, match="none_value_handling has no effect on load"):
            result = mr.load(SimpleData, {"value": "test"}, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == SimpleData(value="test")

    def test_load_no_warning_by_default(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = mr.load(SimpleData, {"value": "test"})
        assert result == SimpleData(value="test")

    def test_load_many_warns(self) -> None:
        with pytest.warns(DeprecationWarning, match="none_value_handling has no effect on load_many"):
            result = mr.load_many(SimpleData, [{"value": "test"}], none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == [SimpleData(value="test")]

    def test_load_many_no_warning_by_default(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = mr.load_many(SimpleData, [{"value": "test"}])
        assert result == [SimpleData(value="test")]
