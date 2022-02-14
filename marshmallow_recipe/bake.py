import dataclasses
import types
from typing import Any, Generic, Mapping, Type, TypeVar, cast

import marshmallow as m
import typing_inspect

from .fields import boolean_field, nested_field, string_field
from .missing import MISSING, MissingType
from .naming_case import DEFAULT_CASE, NamingCase

_T = TypeVar("_T")


def bake_schema(
    cls: Type[_T],
    *,
    naming_case: NamingCase = DEFAULT_CASE,
) -> Type[m.Schema]:
    if not dataclasses.is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    fields = dataclasses.fields(cls)
    schema_class = type(
        cls.__name__,
        (_get_base_schema(cls),),
        {
            field.name: get_field_for(
                field.name,
                field.type,
                _get_field_default(field),
                field.metadata,
                naming_case=naming_case,
            )
            for field in fields
            if field.init
        },
    )
    return cast(Type[m.Schema], schema_class)


def get_field_for(
    name: str,
    type: Type[_T],
    default: _T | MissingType,
    metadata: Mapping[Any, Any],
    *,
    naming_case: NamingCase,
) -> m.fields.Field:
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

    new_name = _try_get_custom_name(metadata) or naming_case(name)

    field_factory = _SIMPLE_TYPE_FIELD_FACTORIES.get(type)
    if field_factory:
        typed_field_factory = cast(_FieldFactory[_T], field_factory)
        return typed_field_factory(required=required, name=new_name, default=default)

    if dataclasses.is_dataclass(type):
        return nested_field(
            bake_schema(type, naming_case=naming_case),
            required=required,
            name=new_name,
            default=default,
        )

    raise ValueError(f"Unsupported {type=}")


def _get_base_schema(cls: Type[_T]) -> Type[m.Schema]:
    class _Schema(m.Schema):  # type: ignore
        @m.post_dump  # type: ignore
        def remove_none_values(self, data: dict[str, Any]) -> dict[str, Any]:
            return {key: value for key, value in data.items() if value is not None}

        @m.post_load  # type: ignore
        def post_load(self, data: dict[str, Any]) -> Any:
            return cls(**data)

    return _Schema


def _get_field_default(field: dataclasses.Field[_T]) -> _T | MissingType:
    default_factory = field.default_factory
    if default_factory is not dataclasses.MISSING:  # type: ignore
        raise ValueError(f"Default factory is not supported for {field}")
    if field.default is not dataclasses.MISSING:
        return field.default
    return MISSING


def _try_get_custom_name(metadata: Mapping[Any, Any]) -> str | None:
    custom_name = metadata.get("name")
    if not custom_name or not isinstance(custom_name, str):
        return None
    return custom_name


class _FieldFactory(Generic[_T]):
    def __call__(
        self,
        required: bool,
        name: str,
        default: _T | MissingType,
        **kwargs: Any,
    ) -> m.fields.Field:
        ...


_SIMPLE_TYPE_FIELD_FACTORIES: dict[type, object] = {
    bool: boolean_field,
    str: string_field,
}
