import dataclasses
import types
from typing import Any, Callable, Generic, Mapping, Type, TypeVar, cast

import marshmallow as m
import typing_inspect

from .fields import boolean, string
from .missing import MISSING, MissingType

_T = TypeVar("_T")


class StrictTypedSchema(Generic[_T], m.Schema):  # type: ignore
    pass


def bake(
    cls: Type[_T],
    *,
    naming_strategy: Callable[[str], str] = lambda x: x,
) -> Type[StrictTypedSchema[_T]]:
    if not dataclasses.is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    return get_schema_for_type(cls, naming_strategy=naming_strategy)


def get_schema_for_type(cls: Type[_T], *, naming_strategy: Callable[[str], str]) -> Type[m.Schema]:
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
                naming_strategy=naming_strategy,
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
    naming_strategy: Callable[[str], str],
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

    new_name = _try_get_custom_name(metadata) or naming_strategy(name)

    field_factory = _SIMPLE_TYPE_FIELD_FACTORIES.get(type)
    if field_factory:
        typed_field_factory = cast(_FieldFactory[_T], field_factory)
        return typed_field_factory(required=required, name=new_name, default=default)

    if dataclasses.is_dataclass(type):
        return m.fields.Nested(
            get_schema_for_type(type, naming_strategy=naming_strategy),
            required=required,
            name=new_name,
            default=default,
        )

    raise ValueError(f"Unsupported {type=}")


def _get_base_schema(cls: Type[_T]) -> Type[StrictTypedSchema[_T]]:
    class _Schema(StrictTypedSchema[_T]):
        def __init__(self, **kwargs: Any):
            kwargs["strict"] = True
            super().__init__(**kwargs)

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
    bool: boolean,
    str: string,
}
