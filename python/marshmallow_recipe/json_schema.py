import collections.abc
import dataclasses
import datetime
import decimal
import enum
import types
import uuid
from typing import Annotated, Any, ClassVar, Literal, Protocol, TypeAliasType, cast, get_args, get_origin

from .generics import TypeLike, get_fields_type_map
from .metadata import EMPTY_METADATA, Metadata, build_metadata
from .missing import MISSING
from .naming_case import NamingCase
from .options import try_get_options_for


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _JsonSchemaContext:
    naming_case: NamingCase | None
    none_value_handling: Any
    decimal_places: int | None
    visited_types: set[TypeLike]
    defs: dict[str, Any]


def json_schema(
    cls: type[Dataclass],
    /,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: Any = None,
    decimal_places: int | None = MISSING,
    title: str | None = None,
) -> dict[str, Any]:
    """Generate JSON Schema Draft 2020-12 from a dataclass.

    Not cached (unlike ``mr.schema``). Handles nested and cyclic dataclasses.

    Args:
        cls: Dataclass type.
        naming_case: Convert field names. Use ``mr.CAMEL_CASE``,
            ``mr.CAPITAL_CAMEL_CASE``, or ``mr.UPPER_SNAKE_CASE``.
        none_value_handling: Controls None field handling in schema.
        decimal_places: Validate maximum decimal places for all Decimal fields.
        title: Override schema title. Defaults to ``@mr.options(title=...)`` or class name.

    Returns:
        JSON Schema dict.
    """
    origin: type = get_origin(cls) or cls
    if not dataclasses.is_dataclass(origin):
        raise ValueError(f"{origin} is not a dataclass")

    options = try_get_options_for(origin)
    if options:
        cls_naming_case = naming_case or options.naming_case
        cls_none_value_handling = none_value_handling or options.none_value_handling
        cls_decimal_places = options.decimal_places if decimal_places is MISSING else decimal_places
        cls_title = options.title if title is None else title
        cls_description = options.description
    else:
        cls_naming_case = naming_case
        cls_none_value_handling = none_value_handling
        cls_decimal_places = decimal_places
        cls_title = title
        cls_description = None

    context = _JsonSchemaContext(
        naming_case=cls_naming_case,
        none_value_handling=cls_none_value_handling,
        decimal_places=cls_decimal_places,
        visited_types=set(),
        defs={},
    )

    schema = __generate_dataclass_schema(cls, context, title=cls_title, description=cls_description)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    if context.defs:
        schema["$defs"] = context.defs

    return schema


def __get_type_name(cls: type) -> str:
    """Get the type name, including generic parameters like Container[int]"""
    # For subscripted generics like Container[int], reconstruct the name from origin and args
    origin = get_origin(cls)
    if origin is not None:
        # It's a subscripted generic - reconstruct name from parts
        args = get_args(cls)
        if args:
            origin_name = origin.__name__  # Use __name__ to avoid test.<locals> prefix
            args_str = ", ".join(__get_type_name(arg) if not hasattr(arg, "__name__") else arg.__name__ for arg in args)
            return f"{origin_name}[{args_str}]"
        return origin.__name__
    # For regular types, use __name__ for simplicity
    return cls.__name__


def __has_default(field: dataclasses.Field) -> bool:
    return field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING  # type: ignore


def __get_default_value(field: dataclasses.Field) -> Any:
    if field.default is not dataclasses.MISSING:
        return field.default
    # Don't evaluate default_factory for JSON Schema - it's dynamic and can't be represented
    return MISSING


def __is_optional(field_type: TypeLike) -> bool:
    underlying_union_types = __try_get_underlying_types_from_union(field_type)
    if underlying_union_types is None:
        return False
    return any(t is types.NoneType for t in underlying_union_types)


__SCALAR_FORMATS: dict[Any, tuple[str, str | None]] = {
    bool: ("boolean", None),
    datetime.datetime: ("string", "date-time"),
    datetime.date: ("string", "date"),
    datetime.time: ("string", "time"),
    uuid.UUID: ("string", "uuid"),
    bytes: ("string", "byte"),
}


def __nullable_type(name: str, nullable: bool) -> str | list[str]:
    return [name, "null"] if nullable else name


def __item_metadata(metadata: Metadata) -> Metadata:
    item_description = metadata.get("item_description")
    if item_description:
        return Metadata({"description": item_description})
    return EMPTY_METADATA


def __apply_length(schema: dict[str, Any], metadata: Metadata, *, item: bool) -> None:
    min_length = metadata.get("min_length")
    max_length = metadata.get("max_length")
    if min_length is not None:
        schema["minItems" if item else "minLength"] = min_length
    if max_length is not None:
        schema["maxItems" if item else "maxLength"] = max_length


def __apply_numeric_bounds(schema: dict[str, Any], metadata: Metadata, *, stringify: bool) -> None:
    for meta_key, schema_key in (
        ("gt", "exclusiveMinimum"),
        ("gte", "minimum"),
        ("lt", "exclusiveMaximum"),
        ("lte", "maximum"),
    ):
        value = metadata.get(meta_key)
        if value is not None:
            schema[schema_key] = str(value) if stringify else value


def __try_get_underlying_types_from_union(t: TypeLike) -> tuple[TypeLike, ...] | None:
    origin = get_origin(t)
    if origin is None:
        return None
    if origin is not types.UnionType and str(origin) != "typing.Union":
        return None
    return get_args(t)


def __generate_dataclass_schema(
    cls: type, context: _JsonSchemaContext, *, title: str | None = None, description: str | None = None
) -> dict[str, Any]:
    """Generate schema for a dataclass, reusing the same context to handle cyclic references"""
    # Get origin for Generic types (Container[int] -> Container)
    origin: type = get_origin(cls) or cls

    # Get options for this class, but allow overrides via parameters
    options = try_get_options_for(origin)
    cls_title = title if title is not None else (options.title if options else None)
    cls_description = description if description is not None else (options.description if options else None)

    fields_type_map = get_fields_type_map(cls)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in dataclasses.fields(origin):
        if not field.init:
            continue

        field_type = fields_type_map[field.name]
        field_metadata = build_metadata(
            name=field.name if context.naming_case is None else context.naming_case(field.name),
            field_metadata=field.metadata,
        )
        field_name = field_metadata["name"]

        field_schema = __convert_field_to_json_schema(field_type, field_metadata, context)

        if __has_default(field):
            default_value = __get_default_value(field)
            if default_value is not MISSING and default_value is not dataclasses.MISSING:
                field_schema["default"] = default_value
        elif not __is_optional(field_type):
            required.append(field_name)

        properties[field_name] = field_schema

    schema: dict[str, Any] = {
        "type": "object",
        "title": __get_type_name(cls) if cls_title is None else cls_title,
        "properties": properties,
        "required": required,
    }

    if cls_description:
        schema["description"] = cls_description

    return schema


def __fill_literal_schema(schema: dict[str, Any], field_type: TypeLike, nullable: bool) -> None:
    literal_values = get_args(field_type)
    json_type: str | None = None
    if literal_values and all(isinstance(v, str) for v in literal_values):
        json_type = "string"
    elif literal_values and all(isinstance(v, bool) for v in literal_values):
        json_type = "boolean"
    elif literal_values and all(isinstance(v, int) and not isinstance(v, bool) for v in literal_values):
        json_type = "integer"
    if json_type is not None:
        schema["type"] = __nullable_type(json_type, nullable)
    enum_values = [v.value if isinstance(v, enum.Enum) else v for v in literal_values]
    schema["enum"] = [*enum_values, None] if nullable else enum_values


def __fill_enum_schema(schema: dict[str, Any], enum_cls: type[enum.Enum], nullable: bool) -> None:
    first_value = next(iter(enum_cls.__members__.values())).value
    if isinstance(first_value, str):
        json_type = "string"
    elif isinstance(first_value, int):
        json_type = "integer"
    else:
        json_type = "string"
    schema["type"] = __nullable_type(json_type, nullable)
    enum_values = [member.value for member in enum_cls.__members__.values()]
    schema["enum"] = [*enum_values, None] if nullable else enum_values


def __fill_ref_schema(
    schema: dict[str, Any], field_type: TypeLike, context: _JsonSchemaContext, nullable: bool
) -> None:
    ref_name = __get_type_name(cast(type, field_type))
    if field_type not in context.visited_types:
        context.visited_types.add(field_type)
        context.defs[ref_name] = __generate_dataclass_schema(cast(type, field_type), context)
    ref = f"#/$defs/{ref_name}"
    if nullable:
        schema["anyOf"] = [{"$ref": ref}, {"type": "null"}]
    else:
        schema["$ref"] = ref


def __build_leaf(
    field_type: TypeLike, metadata: Metadata, context: _JsonSchemaContext, nullable: bool
) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    description = metadata.get("description")
    if description:
        schema["description"] = description

    origin = get_origin(field_type)

    if origin is Literal:
        __fill_literal_schema(schema, field_type, nullable)
        return schema

    if field_type is str:
        schema["type"] = __nullable_type("string", nullable)
        __apply_length(schema, metadata, item=False)
        return schema

    if field_type is int:
        schema["type"] = __nullable_type("integer", nullable)
        __apply_numeric_bounds(schema, metadata, stringify=False)
        return schema

    if field_type is float:
        schema["type"] = __nullable_type("number", nullable)
        __apply_numeric_bounds(schema, metadata, stringify=False)
        return schema

    if field_type is decimal.Decimal:
        schema["type"] = __nullable_type("string", nullable)
        __apply_numeric_bounds(schema, metadata, stringify=True)
        return schema

    scalar = __SCALAR_FORMATS.get(field_type)
    if scalar is not None:
        json_type, fmt = scalar
        schema["type"] = __nullable_type(json_type, nullable)
        if fmt is not None:
            schema["format"] = fmt
        return schema

    args = get_args(field_type)

    if origin is list or origin is collections.abc.Sequence:
        schema["type"] = __nullable_type("array", nullable)
        if args:
            schema["items"] = __convert_field_to_json_schema(args[0], __item_metadata(metadata), context)
        __apply_length(schema, metadata, item=True)
        return schema

    if origin is set or origin is collections.abc.Set or origin is frozenset:
        schema["type"] = __nullable_type("array", nullable)
        schema["uniqueItems"] = True
        if args:
            schema["items"] = __convert_field_to_json_schema(args[0], __item_metadata(metadata), context)
        return schema

    if origin is tuple:
        schema["type"] = __nullable_type("array", nullable)
        if args and len(args) == 2 and args[1] is Ellipsis:
            schema["items"] = __convert_field_to_json_schema(args[0], __item_metadata(metadata), context)
        return schema

    if origin is dict or origin is collections.abc.Mapping:
        schema["type"] = __nullable_type("object", nullable)
        if args and len(args) >= 2 and args[1] is not types.NoneType:
            schema["additionalProperties"] = __convert_field_to_json_schema(args[1], EMPTY_METADATA, context)
        return schema

    field_origin = origin or field_type
    if isinstance(field_origin, type) and dataclasses.is_dataclass(field_origin):
        __fill_ref_schema(schema, field_type, context, nullable)
        return schema

    if isinstance(field_origin, type) and issubclass(field_origin, enum.Enum):
        __fill_enum_schema(schema, field_origin, nullable)
        return schema

    schema["type"] = __nullable_type("object", nullable)
    return schema


def __convert_field_to_json_schema(
    field_type: TypeLike, metadata: Metadata, context: _JsonSchemaContext, *, nullable: bool = False
) -> dict[str, Any]:
    while isinstance(field_type, TypeAliasType):
        field_type = field_type.__value__

    if get_origin(field_type) is Annotated:
        args = get_args(field_type)
        if args:
            underlying_type = args[0]
            annotated_metadata = next((arg for arg in args[1:] if isinstance(arg, Metadata)), EMPTY_METADATA)
            merged_metadata = Metadata(dict(metadata, **annotated_metadata))
            return __convert_field_to_json_schema(underlying_type, merged_metadata, context, nullable=nullable)

    underlying_union_types = __try_get_underlying_types_from_union(field_type)
    if underlying_union_types is not None:
        non_none_types = [t for t in underlying_union_types if t is not types.NoneType]
        nullable = nullable or len(non_none_types) != len(underlying_union_types)

        if len(non_none_types) == 1:
            return __convert_field_to_json_schema(non_none_types[0], metadata, context, nullable=nullable)

        schema: dict[str, Any] = {}
        if metadata.get("description"):
            schema["description"] = metadata["description"]
        if not non_none_types:
            schema["type"] = "null"
            return schema
        branches = [__convert_field_to_json_schema(t, EMPTY_METADATA, context) for t in non_none_types]
        if nullable:
            branches.append({"type": "null"})
        schema["anyOf"] = branches
        return schema

    return __build_leaf(field_type, metadata, context, nullable)
