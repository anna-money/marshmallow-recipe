import dataclasses
import warnings

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SimpleData:
    value: str


class TestLoadNoneValueHandlingDeprecation:
    def test_load_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mr.load(SimpleData, {"value": "test"}, none_value_handling=mr.NoneValueHandling.INCLUDE)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "none_value_handling" in str(w[0].message)

    def test_load_no_warning_by_default(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mr.load(SimpleData, {"value": "test"})
            assert len(w) == 0

    def test_load_many_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mr.load_many(SimpleData, [{"value": "test"}], none_value_handling=mr.NoneValueHandling.INCLUDE)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "none_value_handling" in str(w[0].message)

    def test_load_many_no_warning_by_default(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mr.load_many(SimpleData, [{"value": "test"}])
            assert len(w) == 0
