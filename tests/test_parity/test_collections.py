import json
from typing import Any

from tests.test_parity.conftest import WithCollections


def test_list_of_ints_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[1, 2, 3], list_str=[], dict_str_int={}, set_str=set(), frozenset_int=frozenset(), tuple_str=()
    )
    result = impl.dump(WithCollections, obj)
    expected = (
        '{"dict_str_int": {}, "frozenset_int": [], "list_int": [1, 2, 3], '
        '"list_str": [], "set_str": [], "tuple_str": []}'
    )
    assert result == expected


def test_list_of_strings_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[], list_str=["a", "b", "c"], dict_str_int={}, set_str=set(), frozenset_int=frozenset(), tuple_str=()
    )
    result = impl.dump(WithCollections, obj)
    expected = (
        '{"dict_str_int": {}, "frozenset_int": [], "list_int": [], '
        '"list_str": ["a", "b", "c"], "set_str": [], "tuple_str": []}'
    )
    assert result == expected


def test_empty_list_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[], list_str=[], dict_str_int={}, set_str=set(), frozenset_int=frozenset(), tuple_str=()
    )
    result = impl.dump(WithCollections, obj)
    expected = (
        '{"dict_str_int": {}, "frozenset_int": [], "list_int": [], "list_str": [], "set_str": [], "tuple_str": []}'
    )
    assert result == expected


def test_dict_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[], list_str=[], dict_str_int={"a": 1, "b": 2}, set_str=set(), frozenset_int=frozenset(), tuple_str=()
    )
    result = impl.dump(WithCollections, obj)
    expected = (
        '{"dict_str_int": {"a": 1, "b": 2}, "frozenset_int": [], "list_int": [], '
        '"list_str": [], "set_str": [], "tuple_str": []}'
    )
    assert result == expected


def test_empty_dict_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[], list_str=[], dict_str_int={}, set_str=set(), frozenset_int=frozenset(), tuple_str=()
    )
    result = impl.dump(WithCollections, obj)
    expected = (
        '{"dict_str_int": {}, "frozenset_int": [], "list_int": [], "list_str": [], "set_str": [], "tuple_str": []}'
    )
    assert result == expected


def test_set_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[], list_str=[], dict_str_int={}, set_str={"x", "y", "z"}, frozenset_int=frozenset(), tuple_str=()
    )
    result = impl.dump(WithCollections, obj)
    result_dict = json.loads(result)
    assert set(result_dict["set_str"]) == {"x", "y", "z"}


def test_frozenset_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[], list_str=[], dict_str_int={}, set_str=set(), frozenset_int=frozenset({10, 20, 30}), tuple_str=()
    )
    result = impl.dump(WithCollections, obj)
    result_dict = json.loads(result)
    assert set(result_dict["frozenset_int"]) == {10, 20, 30}


def test_tuple_dump(impl: Any) -> None:
    obj = WithCollections(
        list_int=[],
        list_str=[],
        dict_str_int={},
        set_str=set(),
        frozenset_int=frozenset(),
        tuple_str=("first", "second", "third"),
    )
    result = impl.dump(WithCollections, obj)
    expected = (
        '{"dict_str_int": {}, "frozenset_int": [], "list_int": [], "list_str": [], '
        '"set_str": [], "tuple_str": ["first", "second", "third"]}'
    )
    assert result == expected


def test_collections_load(impl: Any) -> None:
    data = (
        b'{"list_int": [1, 2], "list_str": ["a", "b"], '
        b'"dict_str_int": {"x": 10}, "set_str": ["foo", "bar"], '
        b'"frozenset_int": [100, 200], "tuple_str": ["t1", "t2"]}'
    )
    result = impl.load(WithCollections, data)
    assert result == WithCollections(
        list_int=[1, 2],
        list_str=["a", "b"],
        dict_str_int={"x": 10},
        set_str={"foo", "bar"},
        frozenset_int=frozenset({100, 200}),
        tuple_str=("t1", "t2"),
    )


def test_empty_collections_roundtrip(impl: Any) -> None:
    obj = WithCollections(
        list_int=[], list_str=[], dict_str_int={}, set_str=set(), frozenset_int=frozenset(), tuple_str=()
    )
    dumped = impl.dump(WithCollections, obj)
    loaded = impl.load(WithCollections, dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded == obj
