import collections
import re
import sys

from .bake import bake_schema, get_field_for
from .fields import DateTimeField, DictField, EnumField, FrozenSetField, SetField, TupleField
from .hooks import add_pre_load, pre_load
from .metadata import (
    datetime_metadata,
    decimal_metadata,
    list_metadata,
    metadata,
    sequence_metadata,
    set_metadata,
    tuple_metadata,
)
from .missing import MISSING
from .naming_case import CAMEL_CASE, CAPITAL_CAMEL_CASE, CamelCase, CapitalCamelCase, NamingCase
from .options import NoneValueHandling, options
from .serialization import EmptySchema, dump, dump_many, load, load_many, schema

__all__: tuple[str, ...] = (
    # bake.py
    "bake_schema",
    "get_field_for",
    # hooks.py
    "add_pre_load",
    "pre_load",
    # fields.py
    "DateTimeField",
    "DictField",
    "FrozenSetField",
    "EnumField",
    "SetField",
    "TupleField",
    # metadata.py
    "datetime_metadata",
    "decimal_metadata",
    "list_metadata",
    "metadata",
    "sequence_metadata",
    "set_metadata",
    "tuple_metadata",
    # missing.py
    "MISSING",
    # naming_case.py
    "CAMEL_CASE",
    "CAPITAL_CAMEL_CASE",
    "CamelCase",
    "CapitalCamelCase",
    "NamingCase",
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
)

__version__ = "0.0.26"

version = f"{__version__}, Python {sys.version}"

VersionInfo = collections.namedtuple("VersionInfo", "major minor micro release_level serial")


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
