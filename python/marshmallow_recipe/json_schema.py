import collections.abc
import dataclasses
import datetime
import decimal
import enum
import types
import uuid
from typing import Annotated, Any, ClassVar, Protocol, cast, get_args, get_origin

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


def __convert_field_to_json_schema(
    field_type: TypeLike, metadata: Metadata, context: _JsonSchemaContext
) -> dict[str, Any]:
    schema: dict[str, Any] = {}

    if metadata.get("description"):
        schema["description"] = metadata["description"]

    origin = get_origin(field_type)
    if origin is Annotated:
        args = get_args(field_type)
        if args:
            underlying_type = args[0]
            annotated_metadata = next((arg for arg in args[1:] if isinstance(arg, Metadata)), EMPTY_METADATA)
            merged_metadata = Metadata(dict(metadata, **annotated_metadata))
            return __convert_field_to_json_schema(underlying_type, merged_metadata, context)

    underlying_union_types = __try_get_underlying_types_from_union(field_type)
    if underlying_union_types is not None:
        non_none_types = [t for t in underlying_union_types if t is not types.NoneType]
        if len(non_none_types) == 1:
            field_type = non_none_types[0]
        elif len(non_none_types) > 1:
            schemas = [__convert_field_to_json_schema(t, EMPTY_METADATA, context) for t in non_none_types]
            schema["anyOf"] = schemas
            return schema

    if field_type is str:
        schema["type"] = "string"
        if metadata.get("min_length") is not None:
            schema["minLength"] = metadata["min_length"]
        if metadata.get("max_length") is not None:
            schema["maxLength"] = metadata["max_length"]
        if metadata.get("regexp") is not None:
            schema["pattern"] = metadata["regexp"]
    elif field_type is int:
        schema["type"] = "integer"
    elif field_type is float:
        schema["type"] = "number"
    elif field_type is bool:
        schema["type"] = "boolean"
    elif field_type is datetime.datetime:
        schema["type"] = "string"
        schema["format"] = "date-time"
    elif field_type is datetime.date:
        schema["type"] = "string"
        schema["format"] = "date"
    elif field_type is datetime.time:
        schema["type"] = "string"
        schema["format"] = "time"
    elif field_type is uuid.UUID:
        schema["type"] = "string"
        schema["format"] = "uuid"
    elif field_type is decimal.Decimal:
        # Decimals are always serialized as strings
        schema["type"] = "string"
    else:
        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)
            if origin is list or origin is collections.abc.Sequence:
                schema["type"] = "array"
                if args:
                    item_meta = EMPTY_METADATA
                    if metadata.get("item_description"):
                        item_meta = Metadata({"description": metadata["item_description"]})
                    schema["items"] = __convert_field_to_json_schema(args[0], item_meta, context)
            elif origin is set or origin is collections.abc.Set or origin is frozenset:
                schema["type"] = "array"
                schema["uniqueItems"] = True
                if args:
                    item_meta = EMPTY_METADATA
                    if metadata.get("item_description"):
                        item_meta = Metadata({"description": metadata["item_description"]})
                    schema["items"] = __convert_field_to_json_schema(args[0], item_meta, context)
            elif origin is tuple:
                schema["type"] = "array"
                if args and len(args) == 2 and args[1] is Ellipsis:
                    item_meta = EMPTY_METADATA
                    if metadata.get("item_description"):
                        item_meta = Metadata({"description": metadata["item_description"]})
                    schema["items"] = __convert_field_to_json_schema(args[0], item_meta, context)
            elif origin is dict or origin is collections.abc.Mapping:
                schema["type"] = "object"
                if args and len(args) >= 2 and args[1] is not type(None):
                    schema["additionalProperties"] = __convert_field_to_json_schema(args[1], EMPTY_METADATA, context)
            elif isinstance(origin, type) and dataclasses.is_dataclass(origin):
                # Subscripted generic dataclass like Container[int]
                ref_name = __get_type_name(cast(type, field_type))
                if field_type not in context.visited_types:
                    context.visited_types.add(field_type)
                    nested_schema = __generate_dataclass_schema(cast(type, field_type), context)
                    context.defs[ref_name] = nested_schema
                schema["$ref"] = f"#/$defs/{ref_name}"
            else:
                schema["type"] = "object"
        else:
            # Check if it's a dataclass (non-generic or base case)
            field_origin = get_origin(field_type) or field_type
            if isinstance(field_origin, type) and dataclasses.is_dataclass(field_origin):
                ref_name = __get_type_name(cast(type, field_type))
                # Add to visited_types first to prevent infinite recursion on cyclic references
                if field_type not in context.visited_types:
                    context.visited_types.add(field_type)
                    # Generate the nested schema using internal helper to pass context
                    nested_schema = __generate_dataclass_schema(cast(type, field_type), context)
                    context.defs[ref_name] = nested_schema
                # Always set $ref, even if we already processed this type
                schema["$ref"] = f"#/$defs/{ref_name}"
            elif isinstance(field_origin, type) and issubclass(field_origin, enum.Enum):
                first_value = next(iter(field_origin.__members__.values())).value
                if isinstance(first_value, str):
                    schema["type"] = "string"
                elif isinstance(first_value, int):
                    schema["type"] = "integer"
                else:
                    schema["type"] = "string"
                schema["enum"] = [member.value for member in field_origin.__members__.values()]
            else:
                schema["type"] = "object"

    return schema
