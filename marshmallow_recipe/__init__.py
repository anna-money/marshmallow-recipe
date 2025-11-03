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
from .serialization import EmptySchema, dump, dump_many, load, load_many, schema
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
    # bake.py
    "bake_schema",
    "get_field_for",
    # hooks.py
    "add_pre_load",
    "pre_load",
    # fields.py
    "DateField",
    "DateTimeField",
    "DictField",
    "FrozenSetField",
    "EnumField",
    "SetField",
    "StrField",
    "TupleField",
    "UnionField",
    "NestedField",
    # metadata.py
    "Metadata",
    "EMPTY_METADATA",
    "is_metadata",
    "datetime_metadata",
    "datetime_meta",
    "decimal_metadata",
    "decimal_meta",
    "list_metadata",
    "list_meta",
    "metadata",
    "meta",
    "sequence_metadata",
    "sequence_meta",
    "set_metadata",
    "set_meta",
    "str_metadata",
    "str_meta",
    "time_metadata",
    "tuple_metadata",
    "tuple_meta",
    # missing.py
    "MISSING",
    # naming_case.py
    "CAMEL_CASE",
    "CAPITAL_CAMEL_CASE",
    "CamelCase",
    "CapitalCamelCase",
    "NamingCase",
    "UPPER_SNAKE_CASE",
    "UpperSnakeCase",
    # options.py
    "options",
    "NoneValueHandling",
    # serialization.py
    "load",
    "load_many",
    "dump",
    "dump_many",
    "schema",
    "EmptySchema",
    # validation.py
    "ValidationFunc",
    "email_validate",
    "regexp_validate",
    "validate",
    "ValidationError",
    "ValidationFieldError",
    "get_validation_field_errors",
)

__version__ = "0.0.64"

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
