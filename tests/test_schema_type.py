import dataclasses
from collections.abc import Callable

import marshmallow
import pytest

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Refund:
    refund_id: int


@pytest.mark.parametrize(
    "schema_factory, expected_module",
    [(mr.schema, "marshmallow_recipe.auto_generated"), (mr.nuked.schema, "marshmallow_recipe.nuked.auto_generated")],
)
@pytest.mark.parametrize("many", [False, True])
@pytest.mark.parametrize("naming_case", [None, mr.CAMEL_CASE])
@pytest.mark.parametrize("none_value_handling", [None, mr.NoneValueHandling.INCLUDE])
def test_schema_type_is_named_after_dataclass(
    schema_factory: Callable[..., marshmallow.Schema],
    expected_module: str,
    many: bool,
    naming_case: mr.NamingCase | None,
    none_value_handling: mr.NoneValueHandling | None,
) -> None:
    schema = schema_factory(Refund, many=many, naming_case=naming_case, none_value_handling=none_value_handling)
    schema_type = type(schema)
    assert (schema_type.__name__, schema_type.__qualname__, schema_type.__module__) == (
        "Refund",
        "Refund",
        expected_module,
    )
