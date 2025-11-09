import dataclasses
import types
from collections.abc import Iterable
from contextlib import nullcontext as does_not_raise
from typing import Annotated, Any, ContextManager, TypeVar, Union
from unittest.mock import ANY

import pytest

from marshmallow_recipe.generics import (
    build_subscripted_type,
    extract_type,
    get_class_type_var_map,
    get_fields_class_map,
    get_fields_type_map,
)


@dataclasses.dataclass()
class OtherType:
    pass


@dataclasses.dataclass()
class NonGeneric:
    pass


@dataclasses.dataclass()
class RegularGeneric[T]:
    pass


@dataclasses.dataclass(frozen=True)
class FrozenGeneric[T]:
    pass


def e(match: str) -> ContextManager:
    return pytest.raises(ValueError, match=match)


def type_var_values(type_var_map: dict[Any, Any]) -> list[Any]:
    return sorted(type_var_map.values(), key=repr)


@pytest.mark.parametrize(
    "data, cls, expected, context",
    [
        (1, None, int, does_not_raise()),
        (1, int, int, does_not_raise()),
        (1, OtherType, ANY, e("OtherType'> is invalid but can be removed, actual type is <class 'int'>")),
        (NonGeneric(), None, NonGeneric, does_not_raise()),
        (NonGeneric(), NonGeneric, NonGeneric, does_not_raise()),
        (NonGeneric(), OtherType, ANY, e("OtherType'> is invalid but can be removed, actual type is <class 'tests")),
        (RegularGeneric(), None, ANY, e("Explicit cls required for unsubscripted type <class 'tests")),
        (RegularGeneric(), RegularGeneric, ANY, e("RegularGeneric'> is not subscripted version of <class 'tests")),
        (RegularGeneric(), RegularGeneric[int], RegularGeneric[int], does_not_raise()),
        (RegularGeneric[int](), None, RegularGeneric[int], does_not_raise()),
        (RegularGeneric[int](), RegularGeneric[int], RegularGeneric[int], does_not_raise()),
        (RegularGeneric[int](), RegularGeneric[str], ANY, e("str] is invalid but can be removed, actual type is")),
        (RegularGeneric[int](), RegularGeneric, ANY, e("RegularGeneric'> is invalid but can be removed, actual type")),
        (RegularGeneric[RegularGeneric[int]](), RegularGeneric[RegularGeneric[str]], ANY, e("str]] is invalid but")),
        (RegularGeneric[int](), OtherType, ANY, e("OtherType'> is invalid but can be removed, actual type is tests")),
        (FrozenGeneric[int](), None, ANY, e("Explicit cls required for unsubscripted type <class")),
        (FrozenGeneric[int](), FrozenGeneric[str], FrozenGeneric[str], does_not_raise()),
        (FrozenGeneric(), FrozenGeneric[int], FrozenGeneric[int], does_not_raise()),
        (FrozenGeneric(), FrozenGeneric[list], FrozenGeneric[list], does_not_raise()),
        (FrozenGeneric(), FrozenGeneric[dict], FrozenGeneric[dict], does_not_raise()),
        (FrozenGeneric(), FrozenGeneric[FrozenGeneric[str]], FrozenGeneric[FrozenGeneric[str]], does_not_raise()),
        (FrozenGeneric(), FrozenGeneric, ANY, e("FrozenGeneric'> is not subscripted version of <class 'tests")),
        (FrozenGeneric(), FrozenGeneric[FrozenGeneric], ANY, e("FrozenGeneric] is not subscripted version of")),
        (FrozenGeneric(), OtherType, ANY, e("OtherType'> is not subscripted version of <class 'tests")),
    ],
)
def test_extract_type(data: Any, cls: type, expected: type, context: ContextManager) -> None:
    with context:
        actual = extract_type(data, cls)
        assert actual == expected


def test_get_fields_type_map_with_field_override() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Value1:
        v1: str

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Value2(Value1):
        v2: str

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class T1[TItem]:
        value: Value1
        iterable: Iterable[TItem]

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class T2[TValue: Value1, TItem](T1[TItem]):
        value: TValue
        iterable: set[TItem]

    actual = get_fields_type_map(T2[Value2, int])
    assert actual == {"value": Value2, "iterable": set[int]}


def test_get_fields_type_map_non_generic() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Value1:
        v1: int

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Value2(Value1):
        v2: bool

    actual = get_fields_type_map(Value2)
    assert actual == {"v1": int, "v2": bool}


def test_get_fields_type_map_generic_inheritance() -> None:
    @dataclasses.dataclass()
    class NonGeneric:
        v: bool

    @dataclasses.dataclass()
    class Value1[T]:
        v1: T

    @dataclasses.dataclass()
    class Value2(Value1[int], NonGeneric):
        v2: float

    actual = get_fields_type_map(Value2)
    assert actual == {"v": bool, "v1": int, "v2": float}


def test_get_fields_type_map_non_dataclass() -> None:
    with pytest.raises(ValueError) as e:
        get_fields_type_map(list[int])
    assert e.value.args[0] == "<class 'list'> is not a dataclass"


def test_get_fields_type_map_not_subscripted() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Xxx[T]:
        xxx: T

    with pytest.raises(Exception) as e:
        get_fields_type_map(Xxx)

    assert e.value.args[0] == (
        "Expected subscripted generic, but got unsubscripted "
        "<class 'tests.test_generics.test_get_fields_type_map_not_subscripted.<locals>.Xxx'>"
    )


def test_get_fields_type_map_for_subscripted() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Xxx[T]:
        xxx: T

    actual = get_fields_type_map(Xxx[str])
    assert actual == {"xxx": str}


def test_get_fields_class_map() -> None:
    @dataclasses.dataclass()
    class Base1[T]:
        a: str
        b: str
        c: str

    @dataclasses.dataclass()
    class Base2(Base1[int]):
        a: str
        b: str
        d: str
        e: str

    @dataclasses.dataclass()
    class BaseG:
        f: str
        g: str

    @dataclasses.dataclass()
    class Base3(Base2, BaseG):
        a: str
        d: str
        f: str
        h: str

    actual = get_fields_class_map(Base3)
    assert actual == {"a": Base3, "b": Base2, "c": Base1, "d": Base3, "e": Base2, "f": Base3, "g": BaseG, "h": Base3}


def test_get_class_type_var_map_with_inheritance() -> None:
    @dataclasses.dataclass()
    class NonGeneric:
        pass

    @dataclasses.dataclass()
    class Aaa[T1, T2]:
        pass

    @dataclasses.dataclass()
    class Bbb[T1](Aaa[int, T1]):
        pass

    @dataclasses.dataclass()
    class Ccc[T3]:
        pass

    @dataclasses.dataclass()
    class Ddd[T1, T2, T3](Bbb[T2], Ccc[T1], NonGeneric):
        pass

    actual = get_class_type_var_map(Ddd[bool, str, float])
    assert len(actual) == 4
    assert type_var_values(actual[Aaa]) == [int, str]
    assert type_var_values(actual[Bbb]) == [str]
    assert type_var_values(actual[Ccc]) == [bool]
    assert type_var_values(actual[Ddd]) == [bool, float, str]


def test_get_class_type_var_map_with_incompatible_inheritance() -> None:
    @dataclasses.dataclass()
    class Aaa[T]:
        pass

    @dataclasses.dataclass()
    class Bbb(Aaa[int]):
        pass

    @dataclasses.dataclass()
    class Ccc(Bbb, Aaa[str]):  # type: ignore
        pass

    with pytest.raises(ValueError, match="Incompatible Base class") as e:
        get_class_type_var_map(Ccc)
    assert "<locals>.Aaa'> with generic args {T: <class 'int'>} and {T: <class 'str'>}" in e.value.args[0]


def test_get_class_type_var_map_with_duplicated_generic_inheritance() -> None:
    @dataclasses.dataclass()
    class NonGeneric:
        pass

    @dataclasses.dataclass()
    class Aaa[T]:
        pass

    @dataclasses.dataclass()
    class Bbb(Aaa[int], NonGeneric):
        pass

    @dataclasses.dataclass()
    class Ccc(Bbb, Aaa[int], NonGeneric):
        pass

    actual = get_class_type_var_map(Ccc)
    assert len(actual) == 1
    assert Aaa in actual
    assert type_var_values(actual[Aaa]) == [int]


def test_get_class_type_var_map_with_nesting() -> None:
    @dataclasses.dataclass()
    class Aaa[T1, T2]:
        pass

    @dataclasses.dataclass()
    class Bbb[T1]:
        pass

    @dataclasses.dataclass()
    class Ccc[T1, T2, T3](Aaa[Bbb[list[Annotated[Bbb[T2], "xxx"]]], T1 | None]):
        pass

    actual = get_class_type_var_map(Ccc[bool, str, float])
    assert len(actual) == 2
    assert Aaa in actual and Ccc in actual
    assert len(actual[Aaa]) == 2
    aaa_values = type_var_values(actual[Aaa])
    assert aaa_values[0] == Bbb[list[Annotated[Bbb[str], "xxx"]]]
    assert aaa_values[1] == bool | None
    assert type_var_values(actual[Ccc]) == [bool, float, str]


class Xxx[T1, T2]:
    pass


class Zzz[T1]:
    pass


TInt = TypeVar("TInt")
TIntNone = TypeVar("TIntNone")
TStr = TypeVar("TStr")
TList = TypeVar("TList")
TDictIntTStr = TypeVar("TDictIntTStr")

GENERIC_MAP: dict[TypeVar, type[Any] | types.UnionType] = {
    TInt: int,
    TIntNone: int | None,
    TStr: str,
    TList: list,
    TDictIntTStr: dict[int, TStr],  # type: ignore
}


@pytest.mark.parametrize(
    "t, expected",
    [
        (TIntNone, int | None),
        (list[TInt], list[int]),  # type: ignore
        (list[TIntNone], list[int | None]),  # type: ignore
        (list[TStr], list[str]),  # type: ignore
        (dict[TStr, TInt], dict[str, int]),  # type: ignore
        (dict[TStr, list[TInt]], dict[str, list[int]]),  # type: ignore
        (TInt | None, int | None),
        (bool | None, bool | None),
        (Union[TInt, float, bool, TStr], int | float | bool | str),  # type: ignore
        (TInt | float | bool | TStr, int | float | bool | str),
        (list[TInt | None], list[int | None]),  # type: ignore
        (list[TList], list[list[Any]]),  # type: ignore
        (dict[TInt, TDictIntTStr], dict[int, dict[int, str]]),  # type: ignore
        (Annotated[TStr, "qwe", 123, None], Annotated[str, "qwe", 123, None]),  # type: ignore
        (Annotated[list[TStr], "qwe", 123, None], Annotated[list[str], "qwe", 123, None]),  # type: ignore
        (list[Annotated[list[TInt], "asd", "zxc"]], list[Annotated[list[int], "asd", "zxc"]]),  # type: ignore
        (Xxx[list[TInt], Zzz[TStr]], Xxx[list[int], Zzz[str]]),  # type: ignore
    ],
)
def test_build_subscripted_type(t: type, expected: type) -> None:
    actual = build_subscripted_type(t, GENERIC_MAP)
    assert actual == expected
