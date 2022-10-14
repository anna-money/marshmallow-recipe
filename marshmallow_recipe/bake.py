import dataclasses
import datetime
import decimal
import enum
import inspect
import types
import uuid
from typing import Any, Dict, Generic, List, Mapping, Type, TypeVar, cast

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
    int_field,
    list_field,
    nested_field,
    raw_field,
    str_field,
    uuid_field,
)
from .hooks import get_pre_loads
from .naming_case import NamingCase
from .options import NoneValueHandling, get_options_for

_T = TypeVar("_T")
_MARSHMALLOW_VERSION_MAJOR = int(m.__version__.split(".")[0])


def bake_schema(
    cls: Type[_T],
    *,
    naming_case: NamingCase | None = None,
) -> Type[m.Schema]:
    if not dataclasses.is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    options = get_options_for(cls)
    if naming_case is None:
        naming_case = options.naming_case

    fields = dataclasses.fields(cls)
    schema_class = type(
        cls.__name__,
        (_get_base_schema(cls, options.none_value_handling),),
        {
            field.name: get_field_for(
                field.type,
                _get_metadata(name=naming_case(field.name), default=_get_field_default(field), metadata=field.metadata),
                naming_case=naming_case,
            )
            for field in fields
            if field.init
        },
    )
    return cast(Type[m.Schema], schema_class)


def get_field_for(
    type: Type[_T],
    metadata: Mapping[str, Any],
    *,
    naming_case: NamingCase,
) -> m.fields.Field:
    if type is Any:
        return raw_field(**metadata)

    type = _substitute_any_to_open_generic(type)

    if typing_inspect.is_union_type(type):
        type_args = list(set(typing_inspect.get_args(type, True)))
        if types.NoneType not in type_args or len(type_args) != 2:
            raise ValueError(f"Unsupported {type=}")
        required = False
        type = next(type_arg for type_arg in type_args if type_arg is not types.NoneType)  # noqa
    # to support new union syntax
    elif isinstance(type, types.UnionType):
        type_args = list(set(type.__args__))
        if types.NoneType not in type_args or len(type_args) != 2:
            raise ValueError(f"Unsupported {type=}")
        required = False
        type = next(type_arg for type_arg in type_args if type_arg is not types.NoneType)  # noqa
    else:
        required = True

    field_factory = _SIMPLE_TYPE_FIELD_FACTORIES.get(type)
    if field_factory:
        typed_field_factory = cast(_FieldFactory[_T], field_factory)
        return typed_field_factory(required=required, **metadata)

    if inspect.isclass(type) and issubclass(type, enum.Enum):
        return enum_field(enum_type=type, required=required, **metadata)

    if dataclasses.is_dataclass(type):
        return nested_field(
            bake_schema(type, naming_case=naming_case),
            required=required,
            **metadata,
        )

    if (origin := typing_inspect.get_origin(type)) is not None:
        arguments = typing_inspect.get_args(type, True)
        if origin in (list, List):
            return list_field(
                get_field_for(arguments[0], metadata={}, naming_case=naming_case),
                required=required,
                **metadata,
            )
        if origin in (dict, Dict) and arguments[0] is str and arguments[1] is Any:
            return dict_field(
                required=required,
                **metadata,
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
                result = data
                for pre_load in get_pre_loads(cls):
                    result = pre_load(result)
                return result

        return _Schema


def _get_field_default(field: dataclasses.Field[_T]) -> Any:
    default_factory = field.default_factory
    if default_factory is not dataclasses.MISSING:  # type: ignore
        raise ValueError(f"Default factory is not supported for {field}")
    return field.default


class _FieldFactory(Generic[_T]):
    def __call__(
        self,
        *,
        required: bool,
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


def _get_metadata(*, name: str, default: Any, metadata: Mapping[Any, Any]) -> Mapping[str, Any]:
    result = dict(name=name, default=default)
    result.update({k: v for k, v in metadata.items() if isinstance(k, str)})
    return result


def _substitute_any_to_open_generic(type: type) -> type:
    if type is list:
        return list[Any]
    if type is dict:
        return dict[Any, Any]
    return type
