"""marshmallow-recipe: dataclass serialization powered by marshmallow.

Automatically generates marshmallow schemas from Python dataclasses.
Import convention: import marshmallow_recipe as mr

Core API:
    mr.dump(cls, obj)               Serialize dataclass to dict.
    mr.load(Class, data)            Deserialize dict to dataclass.
    mr.dump_many(cls, objects)      Serialize list of dataclasses.
    mr.load_many(Class, data_list)  Deserialize list of dicts.
    mr.schema(Class)                Get cached marshmallow Schema.

    See help(mr.dump) for serialization details.
    See help(mr.load) for deserialization details.

Field configuration via typing.Annotated (from typing import Annotated):
    Annotated[str, mr.meta(name='custom_name')]
    Annotated[str, mr.str_meta(strip_whitespaces=True)]
    Annotated[decimal.Decimal, mr.decimal_meta(places=2, gt=0)]

    Type-specific metadata (use help(mr.<name>) for details):
        mr.meta, mr.str_meta, mr.int_meta, mr.float_meta, mr.decimal_meta,
        mr.datetime_meta, mr.time_metadata, mr.list_meta, mr.set_meta,
        mr.tuple_meta, mr.frozenset_meta.

Dataclass-level settings:
    @mr.options(naming_case=mr.CAMEL_CASE)
    @mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)

    See help(mr.options) for all settings.

High-performance Rust backend (drop-in replacement, 10-25x faster):
    mr.nuked.dump(cls, obj)
    mr.nuked.load(cls, data)
    mr.nuked.schema(cls)

    See help(mr.nuked) for details.

Additional features:
    mr.json_schema(Class)           JSON Schema Draft 2020-12 generation.
    mr.pre_load                     Pre-load data transformation hook.
    mr.validate                     Validation with custom error messages.
    mr.regexp_validate              Regex-based validation.
    mr.email_validate               Email validation.

    See help(mr.json_schema), help(mr.validate) for details.

Quick example::

    import dataclasses
    import marshmallow_recipe as mr

    @dataclasses.dataclass
    class User:
        name: str
        age: int

    mr.dump(User, User(name='Alice', age=30))
    # {'name': 'Alice', 'age': 30}

    mr.load(User, {'name': 'Alice', 'age': 30})
    # User(name='Alice', age=30)
"""

import sys
from importlib.metadata import version as _get_version

from .bake import bake_schema, get_field_for
from .fields import (
    BytesField,
    DateField,
    DateTimeField,
    DecimalField,
    DictField,
    EnumField,
    FloatField,
    FrozenSetField,
    JsonRawField,
    LiteralField,
    NestedField,
    SetField,
    StrField,
    TupleField,
    UnionField,
)
from .hooks import add_pre_load, pre_load
from .json_schema import json_schema
from .metadata import (
    EMPTY_METADATA,
    Metadata,
    datetime_meta,
    datetime_metadata,
    decimal_meta,
    decimal_metadata,
    float_meta,
    float_metadata,
    frozenset_meta,
    frozenset_metadata,
    int_meta,
    int_metadata,
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
from .serialization import Dataclass, EmptySchema, dump, dump_many, load, load_many, schema
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
    "BytesField",
    "CamelCase",
    "CapitalCamelCase",
    "Dataclass",
    "DateField",
    "DateTimeField",
    "DecimalField",
    "DictField",
    "EmptySchema",
    "EnumField",
    "FloatField",
    "FrozenSetField",
    "JsonRawField",
    "LiteralField",
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
    "email_validate",
    "float_meta",
    "float_metadata",
    "frozenset_meta",
    "frozenset_metadata",
    "get_field_for",
    "get_validation_field_errors",
    "int_meta",
    "int_metadata",
    "is_metadata",
    "json_schema",
    "list_meta",
    "list_metadata",
    "load",
    "load_many",
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

__version__ = _get_version("marshmallow-recipe")

version = f"{__version__}, Python {sys.version}"

from marshmallow_recipe import nuked  # noqa: E402

__all__ = (*__all__, "nuked")  # pyright: ignore[reportUnsupportedDunderAll]
