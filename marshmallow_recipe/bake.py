import collections.abc
import dataclasses
import datetime
import decimal
import enum
import importlib.metadata
import inspect
import types
import uuid
from typing import Annotated, Any, NamedTuple, NewType, Protocol, TypeVar, Union, cast, get_args, get_origin

import marshmallow as m

from .fields import (
    bool_field,
    date_field,
    datetime_field,
    decimal_field,
    dict_field,
    enum_field,
    float_field,
    frozen_set_field,
    int_field,
    list_field,
    nested_field,
    raw_field,
    set_field,
    str_field,
    time_field,
    tuple_field,
    union_field,
    uuid_field,
    with_type_checks_on_serialize,
)
from .generics import TypeLike, get_fields_type_map
from .hooks import get_pre_loads
from .metadata import EMPTY_METADATA, Metadata, is_metadata
from .missing import MISSING
from .naming_case import NamingCase
from .options import NoneValueHandling, try_get_options_for


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _SchemaTypeKey:
    cls: type
    naming_case: NamingCase | None
    none_value_handling: NoneValueHandling | None
    decimal_places: int | None


_T = TypeVar("_T")
_MARSHMALLOW_VERSION_MAJOR = int(importlib.metadata.version("marshmallow").split(".")[0])

_schema_types: dict[_SchemaTypeKey, type[m.Schema]] = {}


class _FieldDescription(NamedTuple):
    field: dataclasses.Field
    value_type: TypeLike
    metadata: Metadata


def bake_schema(
    cls: type,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = MISSING,
) -> type[m.Schema]:
    return _bake_schema(
        cls,
        visited_nested_types={cls},
        naming_case=naming_case,
        none_value_handling=none_value_handling,
        decimal_places=decimal_places,
    )


def _bake_schema(
    cls: type,
    *,
    visited_nested_types: set[TypeLike],
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = MISSING,
) -> type[m.Schema]:
    origin: type = get_origin(cls) or cls
    if not dataclasses.is_dataclass(origin):
        raise ValueError(f"{origin} is not a dataclass")

    if options := try_get_options_for(origin):
        cls_none_value_handling = none_value_handling or options.none_value_handling
        cls_naming_case = naming_case or options.naming_case
        cls_decimal_places = options.decimal_places if decimal_places is MISSING else decimal_places
    else:
        cls_none_value_handling = none_value_handling
        cls_naming_case = naming_case
        cls_decimal_places = decimal_places

    key = _SchemaTypeKey(
        cls=cls,
        naming_case=cls_naming_case,
        none_value_handling=cls_none_value_handling,
        decimal_places=cls_decimal_places,
    )
    if result := _schema_types.get(key):
        return result

    fields_type_map = get_fields_type_map(cls)

    fields = [
        _FieldDescription(
            field,
            fields_type_map[field.name],
            _get_metadata(
                name=field.name if cls_naming_case is None else cls_naming_case(field.name),
                default=_get_field_default(field),
                metadata=field.metadata,
            ),
        )
        for field in dataclasses.fields(origin)
        if field.init
    ]

    for first in fields:
        for second in fields:
            if first is second:
                continue
            second_name = second.metadata["name"]
            if first.field.name == second_name:
                raise ValueError(f"Invalid name={second_name} in metadata for field={second.field.name}")

    schema_type = type(
        cls.__name__,
        (_get_base_schema(cls, cls_none_value_handling or NoneValueHandling.IGNORE),),
        {"__module__": f"{__package__}.auto_generated"}
        | {
            field.name: _get_field_for(
                value_type,
                metadata=metadata,
                visited_nested_types=visited_nested_types,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
                field_decimal_places=cls_decimal_places,
                decimal_places=decimal_places,
            )
            for field, value_type, metadata in fields
        },
    )
    _schema_types[key] = schema_type
    return schema_type


def get_field_for(
    t: TypeLike,
    metadata: Metadata,
    naming_case: NamingCase | None,
    none_value_handling: NoneValueHandling | None,
    decimal_places: int | None = MISSING,
) -> m.fields.Field:
    return _get_field_for(
        t,
        metadata=metadata,
        visited_nested_types=set(),
        naming_case=naming_case,
        none_value_handling=none_value_handling,
        field_decimal_places=decimal_places,
        decimal_places=decimal_places,
    )


def _get_field_for(
    t: TypeLike,
    *,
    metadata: Metadata,
    visited_nested_types: set[TypeLike],
    naming_case: NamingCase | None,
    none_value_handling: NoneValueHandling | None,
    field_decimal_places: int | None,
    decimal_places: int | None,
) -> m.fields.Field:
    if t is Any:
        return raw_field(**metadata)

    underlying_union_types = _try_get_underlying_types_from_union(t)
    # Optional is a union with None
    if underlying_union_types is not None and any(t is types.NoneType for t in underlying_union_types):
        required = False
        allow_none = True
    elif metadata.get("default", dataclasses.MISSING) is not dataclasses.MISSING:
        required = False
        allow_none = False
    else:
        required = True
        allow_none = False

    if underlying_union_types is not None:
        effective_underlying_union_types = [t for t in underlying_union_types if t is not types.NoneType]
        if not effective_underlying_union_types:
            raise ValueError("Union must contain at least one type other than NoneType")
        if len(effective_underlying_union_types) == 1:
            t = effective_underlying_union_types[0]
        else:
            underlying_union_fields = []
            for underlying_type in effective_underlying_union_types:
                underlying_union_fields.append(
                    _get_field_for(
                        underlying_type,
                        metadata=EMPTY_METADATA,
                        visited_nested_types=visited_nested_types,
                        naming_case=naming_case,
                        none_value_handling=none_value_handling,
                        field_decimal_places=field_decimal_places,
                        decimal_places=decimal_places,
                    )
                )
            return union_field(
                fields=underlying_union_fields,
                required=required,
                allow_none=allow_none,
                **metadata,
            )

    if isinstance(t, NewType):
        t = t.__supertype__

    if inspect.isclass(t) and issubclass(t, enum.Enum):
        return enum_field(enum_type=t, required=required, allow_none=allow_none, **metadata)

    if (unsubscripted_type := get_origin(t) or t) and dataclasses.is_dataclass(unsubscripted_type):
        nested_schema: type[m.Schema] | collections.abc.Callable[[], type[m.Schema]]
        is_cyclic_reference = t in visited_nested_types
        visited_nested_types.add(t)
        if is_cyclic_reference:
            nested_schema = lambda: _bake_schema(  # noqa: E731
                cast(type, t),
                visited_nested_types=visited_nested_types,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
                decimal_places=decimal_places,
            )
        else:
            nested_schema = _bake_schema(
                cast(type, t),
                visited_nested_types=visited_nested_types,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
                decimal_places=decimal_places,
            )
        return with_type_checks_on_serialize(
            nested_field(
                nested_schema,
                required=required,
                allow_none=allow_none,
                **metadata,
            ),
            type_guards=unsubscripted_type,  # type: ignore
        )

    if (origin := get_origin(t)) is not None:
        arguments = get_args(t)

        if origin is list or origin is collections.abc.Sequence:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return with_type_checks_on_serialize(
                list_field(
                    _get_field_for(
                        arguments[0],
                        metadata=item_field_metadata,
                        visited_nested_types=visited_nested_types,
                        naming_case=naming_case,
                        none_value_handling=none_value_handling,
                        field_decimal_places=field_decimal_places,
                        decimal_places=decimal_places,
                    ),
                    required=required,
                    allow_none=allow_none,
                    **collection_field_metadata,
                ),
                type_guards=list,
            )

        if origin is set or origin is collections.abc.Set:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return with_type_checks_on_serialize(
                set_field(
                    _get_field_for(
                        arguments[0],
                        metadata=item_field_metadata,
                        visited_nested_types=visited_nested_types,
                        naming_case=naming_case,
                        none_value_handling=none_value_handling,
                        field_decimal_places=field_decimal_places,
                        decimal_places=decimal_places,
                    ),
                    required=required,
                    allow_none=allow_none,
                    **collection_field_metadata,
                ),
                type_guards=set,
            )

        if origin is frozenset:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return with_type_checks_on_serialize(
                frozen_set_field(
                    _get_field_for(
                        arguments[0],
                        metadata=item_field_metadata,
                        visited_nested_types=visited_nested_types,
                        naming_case=naming_case,
                        none_value_handling=none_value_handling,
                        field_decimal_places=field_decimal_places,
                        decimal_places=decimal_places,
                    ),
                    required=required,
                    allow_none=allow_none,
                    **collection_field_metadata,
                ),
                type_guards=frozenset,
            )

        if origin is dict or origin is collections.abc.Mapping:
            keys_field = (
                None
                if arguments[0] is str
                else _get_field_for(
                    arguments[0],
                    metadata=EMPTY_METADATA,
                    visited_nested_types=visited_nested_types,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    field_decimal_places=field_decimal_places,
                    decimal_places=decimal_places,
                )
            )
            values_field = (
                None
                if arguments[1] is Any
                else _get_field_for(
                    arguments[1],
                    metadata=EMPTY_METADATA,
                    visited_nested_types=visited_nested_types,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    field_decimal_places=field_decimal_places,
                    decimal_places=decimal_places,
                )
            )
            return with_type_checks_on_serialize(
                dict_field(keys_field, values_field, required=required, allow_none=allow_none, **metadata),
                type_guards=dict,
            )

        if origin is tuple and len(arguments) == 2 and arguments[1] is Ellipsis:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return with_type_checks_on_serialize(
                tuple_field(
                    _get_field_for(
                        arguments[0],
                        metadata=item_field_metadata,
                        visited_nested_types=visited_nested_types,
                        naming_case=naming_case,
                        none_value_handling=none_value_handling,
                        field_decimal_places=field_decimal_places,
                        decimal_places=decimal_places,
                    ),
                    required=required,
                    allow_none=allow_none,
                    **collection_field_metadata,
                ),
                type_guards=tuple,
            )

        if origin is Annotated:
            underlying_type, *annotations = arguments
            annotated_metadata = next(
                (annotation for annotation in annotations if is_metadata(annotation)), EMPTY_METADATA
            )
            metadata = Metadata(dict(metadata, **annotated_metadata))

            return _get_field_for(
                underlying_type,
                metadata=metadata,
                visited_nested_types=visited_nested_types,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
                field_decimal_places=field_decimal_places,
                decimal_places=decimal_places,
            )

    if t in _SIMPLE_TYPE_FIELD_FACTORIES:
        field_factory = _SIMPLE_TYPE_FIELD_FACTORIES[t]
        field_kwargs: dict[str, Any] = dict(required=required, allow_none=allow_none, **metadata)

        if t is decimal.Decimal and field_decimal_places is not MISSING:
            field_kwargs.setdefault("places", field_decimal_places)

        return with_type_checks_on_serialize(
            field_factory(**field_kwargs),
            type_guards=(float, int) if t == float else t,
        )

    raise ValueError(f"Unsupported {t=}")


if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def _get_base_schema(cls: type, none_value_handling: NoneValueHandling) -> type[m.Schema]:
        class _Schema(m.Schema):
            class Meta:  # type: ignore
                unknown = m.EXCLUDE  # type: ignore

            @property
            def set_class(self) -> type:
                return m.schema.OrderedSet  # type: ignore

            @m.post_dump
            def remove_none_values(self, data: dict[str, Any], **_: Any) -> dict[str, Any]:
                if none_value_handling == NoneValueHandling.IGNORE:
                    return {key: value for key, value in data.items() if value is not None}
                return data

            @m.post_load
            def post_load(self, data: dict[str, Any], **_: Any) -> Any:
                return cls(**data)

            @m.pre_load
            def pre_load(self, data: dict[str, Any], **_: Any) -> Any:
                result = data
                for pre_load in get_pre_loads(cls):
                    result = pre_load(result)
                return result

        return _Schema

else:

    def _get_base_schema(cls: type, none_value_handling: NoneValueHandling) -> type[m.Schema]:
        class _Schema(m.Schema):  # type: ignore
            @property
            def set_class(self) -> type:
                return m.schema.OrderedSet  # type: ignore

            @m.post_dump  # type: ignore
            def remove_none_values(self, data: dict[str, Any]) -> dict[str, Any]:
                if none_value_handling == NoneValueHandling.IGNORE:
                    return {key: value for key, value in data.items() if value is not None}
                return data

            @m.post_load  # type: ignore
            def post_load(self, data: dict[str, Any]) -> Any:
                return cls(**data)

            @m.pre_load  # type: ignore
            def pre_load(self, data: dict[str, Any]) -> Any:
                if not isinstance(data, dict):  # type: ignore
                    return data
                # Exclude unknown fields to prevent possible value overlapping
                known_fields = {field.load_from or field.name for field in self.fields.values()}  # type: ignore
                result = {key: value for key, value in data.items() if key in known_fields}
                for pre_load in get_pre_loads(cls):
                    result = pre_load(result)
                return result

        return _Schema


def _get_field_default(field: dataclasses.Field) -> Any:
    default_factory = field.default_factory
    if default_factory is not dataclasses.MISSING:  # type: ignore
        return default_factory
    return field.default


class _FieldFactory(Protocol):
    def __call__(
        self,
        *,
        required: bool,
        allow_none: bool,
        name: str,
        default: Any,
        **kwargs: Any,
    ) -> m.fields.Field: ...


_SIMPLE_TYPE_FIELD_FACTORIES: dict[type, _FieldFactory] = {
    bool: bool_field,
    str: str_field,
    decimal.Decimal: decimal_field,
    int: int_field,
    float: float_field,
    uuid.UUID: uuid_field,
    datetime.datetime: datetime_field,
    datetime.date: date_field,
    datetime.time: time_field,
}


def _get_metadata(*, name: str, default: Any, metadata: collections.abc.Mapping[Any, Any]) -> Metadata:
    values: dict[str, Any] = dict(name=name, default=default)
    values.update({k: v for k, v in metadata.items() if isinstance(k, str)})
    return Metadata(values)


def _try_get_underlying_types_from_union(t: TypeLike) -> tuple[TypeLike, ...] | None:
    # to support Union[int, None] and int | None
    if not get_origin(t) is Union and not isinstance(t, types.UnionType):  # type: ignore
        return None
    return get_args(t)
