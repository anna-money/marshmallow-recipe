import collections.abc
import dataclasses
import datetime
import decimal
import enum
import inspect
import types
import uuid
from typing import Any, Protocol, Type, TypeVar, cast

import marshmallow as m
import typing_inspect

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
    tuple_field,
    uuid_field,
)
from .hooks import get_pre_loads
from .naming_case import NamingCase
from .options import NoneValueHandling, try_get_options_for


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _SchemaTypeKey:
    cls: type
    naming_case: NamingCase | None
    none_value_handling: NoneValueHandling | None


_T = TypeVar("_T")
_MARSHMALLOW_VERSION_MAJOR = int(m.__version__.split(".")[0])
_schema_types: dict[_SchemaTypeKey, Type[m.Schema]] = {}


def bake_schema(
    cls: Type[_T], *, naming_case: NamingCase | None = None, none_value_handling: NoneValueHandling | None = None
) -> Type[m.Schema]:
    if not dataclasses.is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    if options := try_get_options_for(cls):
        cls_none_value_handling = none_value_handling or options.none_value_handling
        cls_naming_case = naming_case or options.naming_case
    else:
        cls_none_value_handling = none_value_handling
        cls_naming_case = naming_case

    key = _SchemaTypeKey(cls=cls, naming_case=cls_naming_case, none_value_handling=cls_none_value_handling)
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

    schema_class = type(
        cls.__name__,
        (_get_base_schema(cls, cls_none_value_handling or NoneValueHandling.IGNORE),),
        {"__module__": f"{__package__}.auto_generated"}
        | {
            field.name: get_field_for(
                field.type, metadata, naming_case=naming_case, none_value_handling=none_value_handling
            )
            for field, metadata in fields_with_metadata
        },
    )
    result = cast(Type[m.Schema], schema_class)
    _schema_types[key] = result
    return result


def get_field_for(
    type: Type[_T],
    metadata: collections.abc.Mapping[str, Any],
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

    field_factory = _SIMPLE_TYPE_FIELD_FACTORIES.get(type)
    if field_factory:
        typed_field_factory = cast(_FieldFactory, field_factory)
        return typed_field_factory(required=required, allow_none=allow_none, **metadata)

    if inspect.isclass(type) and issubclass(type, enum.Enum):
        return enum_field(enum_type=type, required=required, allow_none=allow_none, **metadata)

    if dataclasses.is_dataclass(type):
        return nested_field(
            bake_schema(type, naming_case=naming_case, none_value_handling=none_value_handling),
            required=required,
            allow_none=allow_none,
            **metadata,
        )

    if (origin := typing_inspect.get_origin(type)) is not None:
        arguments = typing_inspect.get_args(type, True)

        if origin is list or origin is collections.abc.Sequence:
            collection_field_metadata = dict(metadata)
            if validate_item := collection_field_metadata.pop("validate_item", None):
                item_field_metadata = dict(validate=validate_item)
            else:
                item_field_metadata = {}

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
                item_field_metadata = dict(validate=validate_item)
            else:
                item_field_metadata = {}

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
                item_field_metadata = dict(validate=validate_item)
            else:
                item_field_metadata = {}

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
                    arguments[0], metadata={}, naming_case=naming_case, none_value_handling=none_value_handling
                )
            )
            values_field = (
                None
                if arguments[1] is Any
                else get_field_for(
                    arguments[1], metadata={}, naming_case=naming_case, none_value_handling=none_value_handling
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
                item_field_metadata = dict(validate=validate_item)
            else:
                item_field_metadata = {}

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

    raise ValueError(f"Unsupported {type=}")


if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def _get_base_schema(cls: Type[_T], none_value_handling: NoneValueHandling) -> Type[m.Schema]:
        class _Schema(m.Schema):
            class Meta:
                unknown = m.EXCLUDE

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

    def _get_base_schema(cls: Type[_T], none_value_handling: NoneValueHandling) -> Type[m.Schema]:
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


def _get_field_default(field: dataclasses.Field[_T]) -> Any:
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


_SIMPLE_TYPE_FIELD_FACTORIES: dict[type, object] = {
    bool: bool_field,
    str: str_field,
    decimal.Decimal: decimal_field,
    int: int_field,
    float: float_field,
    uuid.UUID: uuid_field,
    datetime.datetime: datetime_field,
    datetime.date: date_field,
}


def _get_metadata(
    *, name: str, default: Any, metadata: collections.abc.Mapping[Any, Any]
) -> collections.abc.Mapping[str, Any]:
    result = dict(name=name, default=default)
    result.update({k: v for k, v in metadata.items() if isinstance(k, str)})
    return result


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
    if typing_inspect.is_union_type(type):
        type_args = list(set(typing_inspect.get_args(type, True)))
        if types.NoneType not in type_args or len(type_args) != 2:
            raise ValueError(f"Unsupported {type=}")
        return next(type_arg for type_arg in type_args if type_arg is not types.NoneType)  # noqa

    # to support new union syntax
    if isinstance(type, types.UnionType):
        type_args = list(set(type.__args__))
        if types.NoneType not in type_args or len(type_args) != 2:
            raise ValueError(f"Unsupported {type=}")
        return next(type_arg for type_arg in type_args if type_arg is not types.NoneType)  # noqa

    return None
