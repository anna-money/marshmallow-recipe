import dataclasses
import json
from typing import Any

import marshmallow
import pytest

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStr:
    value: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithInt:
    value: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithAny:
    value: Any


class TestBytesParserJsonLoadsParity:
    @pytest.mark.parametrize(
        "data",
        [
            rb'{"value":"a\tb\n\r\"c\\d\/e\b\f"}',
            '{"value":"é—你"}'.encode(),
            '{"value":"\U0001f600"}'.encode(),
            '{"value":"café—你好"}'.encode(),
            rb'{"value":""}',
            rb'{  "value"  :  "spaced"  }',
            b'{\n\t"value"\r:\n"ws"\n}',
        ],
    )
    def test_string_escapes_and_unicode(self, data: bytes) -> None:
        assert mr.nuked.load_from_bytes(WithStr, data) == mr.nuked.load(WithStr, json.loads(data))

    @pytest.mark.parametrize(
        "data", [b'{"value":42}', b'{"value":-7}', b'{"value":12345678901234567890123456789}', b'{"value":0}']
    )
    def test_numbers(self, data: bytes) -> None:
        assert mr.nuked.load_from_bytes(WithInt, data) == mr.nuked.load(WithInt, json.loads(data))

    @pytest.mark.parametrize(
        "data",
        [
            b'{"value":1.5}',
            b'{"value":-0.0}',
            b'{"value":1e10}',
            b'{"value":1E-5}',
            b'{"value":[1,2.5,null,true,false,"x"]}',
            b'{"value":{"a":1,"b":[2,3]}}',
        ],
    )
    def test_any_materializer_matches_json_loads(self, data: bytes) -> None:
        assert mr.nuked.load_from_bytes(WithAny, data) == mr.nuked.load(WithAny, json.loads(data))

    def test_duplicate_key_last_wins(self) -> None:
        data = b'{"value":"first","value":"second"}'
        assert mr.nuked.load_from_bytes(WithStr, data) == WithStr(value="second")
        assert json.loads(data) == {"value": "second"}

    def test_unknown_keys_ignored(self) -> None:
        data = b'{"value":"v","extra":[1,2,{"q":null}],"more":"x"}'
        assert mr.nuked.load_from_bytes(WithStr, data) == WithStr(value="v")

    @pytest.mark.parametrize(
        "data",
        [
            b'{"value":01}',
            b'{"value":00}',
            b'{"value":"a",}',
            b'{"value":"a"',
            b'{"value" "a"}',
            b'{value:"a"}',
            b'{"value":"a"}trailing',
            b'{"value":}',
            b"",
            b'{"value":"unterminated}',
        ],
    )
    def test_malformed_raises_validation_error(self, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError):
            mr.nuked.load_from_bytes(WithStr, data)

    def test_nesting_within_limit(self) -> None:
        depth = 100
        data = ('{"value":' + "[" * depth + "1" + "]" * depth + "}").encode()
        assert mr.nuked.load_from_bytes(WithAny, data) == mr.nuked.load(WithAny, json.loads(data))

    def test_nesting_exceeds_limit_raises(self) -> None:
        depth = 5000
        data = ('{"value":' + "[" * depth + "1" + "]" * depth + "}").encode()
        with pytest.raises(marshmallow.ValidationError):
            mr.nuked.load_from_bytes(WithAny, data)

    def test_special_floats_rejected_by_float_field(self) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithFloat:
            value: float

        for data in (b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}'):
            with pytest.raises(marshmallow.ValidationError):
                mr.nuked.load_from_bytes(WithFloat, data)

    def test_round_trip(self) -> None:
        obj = WithStr(value='quote " backslash \\ slash / tab \t newline \n é 😀')
        assert mr.nuked.load_from_bytes(WithStr, mr.nuked.dump_to_bytes(WithStr, obj)) == obj
