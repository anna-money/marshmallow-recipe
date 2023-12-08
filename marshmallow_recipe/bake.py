import collections.abc
import dataclasses
import datetime
import decimal
import enum
import inspect
import types
import uuid
from typing import Annotated, Any, Protocol, TypeVar, Union, get_args, get_origin

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
    uuid_field,
)
from .hooks import get_pre_loads
from .metadata import EMPTY_METADATA, Metadata, is_metadata
from .naming_case import NamingCase
from .options import NoneValueHandling, try_get_options_for


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _SchemaTypeKey:
    cls: type
    naming_case: NamingCase | None
    none_value_handling: NoneValueHandling | None


_T = TypeVar("_T")
_MARSHMALLOW_VERSION_MAJOR = int(m.__version__.split(".")[0])
_schema_types: dict[_SchemaTypeKey, type[m.Schema]] = {}


def bake_schema(
    cls: type,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
) -> type[m.Schema]:
    if not dataclasses.is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    if options := try_get_options_for(cls):
        cls_none_value_handling = none_value_handling or options.none_value_handling
        cls_naming_case = naming_case or options.naming_case
    else:
        cls_none_value_handling = none_value_handling
        cls_naming_case = naming_case

    key = _SchemaTypeKey(
        cls=cls,
        naming_case=cls_naming_case,
        none_value_handling=cls_none_value_handling,
    )
    if result := _schema_types.get(key):
        return result

    fields_with_metadata = [
        (
            field,
            _get_metadata(
                name=field.name if cls_naming_case is None else cls_naming_case(field.name),
                default=_get_field_default(field),
                metadata=field.metadata,
            ),
        )
        for field in dataclasses.fields(cls)
        if field.init
    ]

    for field, _ in fields_with_metadata:
        for other_field, metadata in fields_with_metadata:
            if field is other_field:
                continue

            other_field_name = metadata["name"]
            if field.name == other_field_name:
                raise ValueError(f"Invalid name={other_field_name} in metadata for field={other_field.name}")

    schema_type: type[m.Schema] = type(
        cls.__name__,
        (_get_base_schema(cls, cls_none_value_handling or NoneValueHandling.IGNORE),),
        {"__module__": f"{__package__}.auto_generated"}
        | {
            field.name: get_field_for(
                field.type,
                metadata,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
            )
            for field, metadata in fields_with_metadata
        },
    )
    _schema_types[key] = schema_type
    return schema_type


def get_field_for(
    type: type,
    metadata: Metadata,
    naming_case: NamingCase | None,
    none_value_handling: NoneValueHandling | None,
) -> m.fields.Field:
    if type is Any:
        return raw_field(**metadata)

    type = _substitute_any_to_open_generic(type)

    if underlying_type_from_optional := _try_get_underlying_type_from_optional(type):
        required = False
        allow_none = True
        type = underlying_type_from_optional
    elif metadata.get("default", dataclasses.MISSING) is not dataclasses.MISSING:
        required = False
        allow_none = False
    else:
        required = True
        allow_none = False

    if inspect.isclass(type) and issubclass(type, enum.Enum):
        return enum_field(enum_type=type, required=required, allow_none=allow_none, **metadata)

    if dataclasses.is_dataclass(type):
        return nested_field(
            bake_schema(type, naming_case=naming_case, none_value_handling=none_value_handling),
            required=required,
            allow_none=allow_none,
            **metadata,
        )

    if (origin := get_origin(type)) is not None:
        arguments = get_args(type)

        if origin is list or origin is collections.abc.Sequence:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return list_field(
                get_field_for(
                    arguments[0],
                    metadata=item_field_metadata,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                ),
                required=required,
                allow_none=allow_none,
                **collection_field_metadata,
            )

        if origin is set or origin is collections.abc.Set:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return set_field(
                get_field_for(
                    arguments[0],
                    metadata=item_field_metadata,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                ),
                required=required,
                allow_none=allow_none,
                **collection_field_metadata,
            )

        if origin is frozenset:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return frozen_set_field(
                get_field_for(
                    arguments[0],
                    metadata=item_field_metadata,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                ),
                required=required,
                allow_none=allow_none,
                **collection_field_metadata,
            )

        if origin is dict or origin is collections.abc.Mapping:
            keys_field = (
                None
                if arguments[0] is str
                else get_field_for(
                    arguments[0],
                    metadata=EMPTY_METADATA,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                )
            )
            values_field = (
                None
                if arguments[1] is Any
                else get_field_for(
                    arguments[1],
                    metadata=EMPTY_METADATA,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                )
            )

            return dict_field(
                keys_field,
                values_field,
                required=required,
                allow_none=allow_none,
                **metadata,
            )

        if origin is tuple and len(arguments) == 2 and arguments[1] is Ellipsis:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = Metadata(dict(validate=validate_item))
            else:
                item_field_metadata = EMPTY_METADATA

            return tuple_field(
                get_field_for(
                    arguments[0],
                    metadata=item_field_metadata,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                ),
                required=required,
                allow_none=allow_none,
                **collection_field_metadata,
            )

        if origin is Annotated:
            underlying_type, *annotations = arguments
            annotated_metadata = next(
                (annotation for annotation in annotations if is_metadata(annotation)), EMPTY_METADATA
            )
            metadata = Metadata(dict(metadata, **annotated_metadata))

            return get_field_for(
                underlying_type,
                metadata=metadata,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
            )

    field_factory = _SIMPLE_TYPE_FIELD_FACTORIES.get(type)
    if field_factory:
        return field_factory(required=required, allow_none=allow_none, **metadata)

    raise ValueError(f"Unsupported {type=}")


if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def _get_base_schema(cls: type, none_value_handling: NoneValueHandling) -> type[m.Schema]:
        class _Schema(m.Schema):
            class Meta:  # type: ignore
                unknown = m.EXCLUDE  # type: ignore

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
    ) -> m.fields.Field:
        ...


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


def _substitute_any_to_open_generic(type: type) -> type:
    if type is list:
        return list[Any]
    if type is set:
        return set[Any]
    if type is frozenset:
        return frozenset[Any]
    if type is dict:
        return dict[Any, Any]
    if type is tuple:
        return tuple[Any, ...]
    return type


def _try_get_underlying_type_from_optional(type: type) -> type | None:
    # to support Union[int, None] and int | None
    if get_origin(type) is Union or isinstance(type, types.UnionType):
        type_args = get_args(type)
        if types.NoneType not in type_args or len(type_args) != 2:
            raise ValueError(f"Unsupported {type=}")
        return next(type_arg for type_arg in type_args if type_arg is not types.NoneType)  # noqa

    return None
