import collections
import re
import sys

from .bake import bake_schema, get_field_for
from .fields import (
    DateField,
    DateTimeField,
    DictField,
    EnumField,
    FrozenSetField,
    NestedField,
    SetField,
    StrField,
    TupleField,
    UnionField,
)
from .hooks import add_pre_load, pre_load
from .metadata import (
    EMPTY_METADATA,
    Metadata,
    datetime_meta,
    datetime_metadata,
    decimal_meta,
    decimal_metadata,
    is_metadata,
    list_meta,
    list_metadata,
    meta,
    metadata,
    sequence_meta,
    sequence_metadata,
    set_meta,
    set_metadata,
    str_meta,
    str_metadata,
    time_metadata,
    tuple_meta,
    tuple_metadata,
)
from .missing import MISSING
from .naming_case import (
    CAMEL_CASE,
    CAPITAL_CAMEL_CASE,
    UPPER_SNAKE_CASE,
    CamelCase,
    CapitalCamelCase,
    NamingCase,
    UpperSnakeCase,
)
from .options import NoneValueHandling, options
from .serialization import Dataclass, EmptySchema, dump, dump_many, dump_value, load, load_many, load_value, schema
from .validation import (
    ValidationError,
    ValidationFieldError,
    ValidationFunc,
    email_validate,
    get_validation_field_errors,
    regexp_validate,
    validate,
)

__all__: tuple[str, ...] = (
    "CAMEL_CASE",
    "CAPITAL_CAMEL_CASE",
    "EMPTY_METADATA",
    "MISSING",
    "UPPER_SNAKE_CASE",
    "CamelCase",
    "CapitalCamelCase",
    "Dataclass",
    "DateField",
    "DateTimeField",
    "DictField",
    "EmptySchema",
    "EnumField",
    "FrozenSetField",
    "Metadata",
    "NamingCase",
    "NestedField",
    "NoneValueHandling",
    "SetField",
    "StrField",
    "TupleField",
    "UnionField",
    "UpperSnakeCase",
    "ValidationError",
    "ValidationFieldError",
    "ValidationFunc",
    "add_pre_load",
    "bake_schema",
    "datetime_meta",
    "datetime_metadata",
    "decimal_meta",
    "decimal_metadata",
    "dump",
    "dump_many",
    "dump_value",
    "email_validate",
    "get_field_for",
    "get_validation_field_errors",
    "is_metadata",
    "list_meta",
    "list_metadata",
    "load",
    "load_many",
    "load_value",
    "meta",
    "metadata",
    "options",
    "pre_load",
    "regexp_validate",
    "schema",
    "sequence_meta",
    "sequence_metadata",
    "set_meta",
    "set_metadata",
    "str_meta",
    "str_metadata",
    "time_metadata",
    "tuple_meta",
    "tuple_metadata",
    "validate",
)

__version__ = "0.0.67"

version = f"{__version__}, Python {sys.version}"

VersionInfo = collections.namedtuple("VersionInfo", "major minor micro release_level serial")  # type: ignore


def _parse_version(v: str) -> VersionInfo:
    version_re = r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)" r"((?P<release_level>[a-z]+)(?P<serial>\d+)?)?$"
    match = re.match(version_re, v)
    if not match:
        raise ImportError(f"Invalid package version {v}")
    try:
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        micro = int(match.group("micro"))
        levels = {"rc": "candidate", "a": "alpha", "b": "beta", None: "final"}
        release_level = levels[match.group("release_level")]
        serial = int(match.group("serial")) if match.group("serial") else 0
        return VersionInfo(major, minor, micro, release_level, serial)
    except Exception as e:
        raise ImportError(f"Invalid package version {v}") from e


version_info = _parse_version(__version__)
