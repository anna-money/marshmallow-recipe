#![allow(clippy::struct_field_names)]

use pyo3::prelude::*;
use rust_decimal::RoundingStrategy;

pub use crate::fields::collection::CollectionKind;
pub use crate::fields::datetime::DateTimeFormat;
pub use crate::fields::nested::{DataclassDumperSchema, FieldDumper};
use crate::types::{DecimalPlaces, DumpContext};

pub use crate::fields::nested::nested_dumper::dump_dataclass;

pub struct StrEnumData {
    pub enum_cls: Py<PyAny>,
    pub enum_name: Option<String>,
    pub enum_members_repr: Option<String>,
}

impl Clone for StrEnumData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            enum_cls: self.enum_cls.clone_ref(py),
            enum_name: self.enum_name.clone(),
            enum_members_repr: self.enum_members_repr.clone(),
        })
    }
}

pub struct IntEnumData {
    pub enum_cls: Py<PyAny>,
    pub enum_name: Option<String>,
    pub enum_members_repr: Option<String>,
}

impl Clone for IntEnumData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            enum_cls: self.enum_cls.clone_ref(py),
            enum_name: self.enum_name.clone(),
            enum_members_repr: self.enum_members_repr.clone(),
        })
    }
}

#[derive(Clone)]
pub struct DecimalData {
    pub decimal_places: DecimalPlaces,
    pub rounding_strategy: Option<RoundingStrategy>,
    pub invalid_error: Option<String>,
}

pub struct CollectionData {
    pub item: Box<Dumper>,
    pub item_validator: Option<Py<PyAny>>,
    pub kind: CollectionKind,
}

impl Clone for CollectionData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            item: self.item.clone(),
            item_validator: self.item_validator.as_ref().map(|v| v.clone_ref(py)),
            kind: self.kind,
        })
    }
}

pub struct DictData {
    pub value: Box<Dumper>,
    pub value_validator: Option<Py<PyAny>>,
}

impl Clone for DictData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            value: self.value.clone(),
            value_validator: self.value_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

impl std::fmt::Debug for Dumper {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Str { strip_whitespaces } => f.debug_struct("Str").field("strip_whitespaces", strip_whitespaces).finish(),
            Self::Int => write!(f, "Int"),
            Self::Float => write!(f, "Float"),
            Self::Bool => write!(f, "Bool"),
            Self::Decimal(_) => write!(f, "Decimal"),
            Self::Date => write!(f, "Date"),
            Self::Time => write!(f, "Time"),
            Self::DateTime { format } => f.debug_struct("DateTime").field("format", format).finish(),
            Self::Uuid => write!(f, "Uuid"),
            Self::StrEnum(_) => write!(f, "StrEnum"),
            Self::IntEnum(_) => write!(f, "IntEnum"),
            Self::Any => write!(f, "Any"),
            Self::Collection(_) => write!(f, "Collection"),
            Self::Dict(_) => write!(f, "Dict"),
            Self::Nested { .. } => write!(f, "Nested"),
            Self::Union { .. } => write!(f, "Union"),
        }
    }
}

#[derive(Clone)]
pub enum Dumper {
    Str { strip_whitespaces: bool },
    Int,
    Float,
    Bool,
    Decimal(Box<DecimalData>),
    Date,
    Time,
    DateTime { format: DateTimeFormat },
    Uuid,
    StrEnum(Box<StrEnumData>),
    IntEnum(Box<IntEnumData>),
    Any,
    Collection(Box<CollectionData>),
    Dict(Box<DictData>),
    Nested { schema: Box<DataclassDumperSchema> },
    Union { variants: Vec<Self> },
}

impl Dumper {
    pub fn can_dump<'py>(
        &self,
        value: &Bound<'py, PyAny>,
        ctx: &DumpContext<'_, 'py>,
    ) -> bool {
        use crate::fields::{str_type, int, float, bool_type, decimal, date, time, datetime, uuid, str_enum, any, collection, dict, nested, union};

        match self {
            Self::Str { .. } => str_type::str_dumper::can_dump(value),
            Self::Int => int::int_dumper::can_dump(value),
            Self::Float => float::float_dumper::can_dump(value),
            Self::Bool => bool_type::bool_dumper::can_dump(value),
            Self::Decimal(_) => decimal::decimal_dumper::can_dump(value, ctx),
            Self::Date => date::date_dumper::can_dump(value),
            Self::Time => time::time_dumper::can_dump(value),
            Self::DateTime { .. } => datetime::datetime_dumper::can_dump(value),
            Self::Uuid => uuid::uuid_dumper::can_dump(value),
            Self::StrEnum(data) => str_enum::str_enum_dumper::can_dump(value, ctx, &data.enum_cls),
            Self::IntEnum(data) => str_enum::int_enum_dumper::can_dump(value, ctx, &data.enum_cls),
            Self::Any => any::any_dumper::can_dump(value),
            Self::Collection(data) => collection::collection_dumper::can_dump(value, ctx, data.kind, &data.item),
            Self::Dict(data) => dict::dict_dumper::can_dump(value, ctx, &data.value),
            Self::Nested { schema } => nested::nested_dumper::can_dump(value, ctx, schema),
            Self::Union { variants } => union::union_dumper::can_dump(value, ctx, variants),
        }
    }

    pub fn dump_to_dict<'py>(
        &self,
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        use crate::fields::{str_type, int, float, bool_type, decimal, date, time, datetime, uuid, str_enum, any, collection, dict, nested, union};

        match self {
            Self::Str { strip_whitespaces } => {
                str_type::str_dumper::dump_to_dict(value, field_name, ctx, *strip_whitespaces)
            }
            Self::Int => int::int_dumper::dump_to_dict(value, field_name, ctx),
            Self::Float => float::float_dumper::dump_to_dict(value, field_name, ctx),
            Self::Bool => bool_type::bool_dumper::dump_to_dict(value, field_name, ctx),
            Self::Decimal(data) => {
                decimal::decimal_dumper::dump_to_dict(
                    value,
                    field_name,
                    ctx,
                    data.decimal_places,
                    data.rounding_strategy,
                    data.invalid_error.as_deref(),
                )
            }
            Self::Date => date::date_dumper::dump_to_dict(value, field_name, ctx),
            Self::Time => time::time_dumper::dump_to_dict(value, field_name, ctx),
            Self::DateTime { format } => {
                datetime::datetime_dumper::dump_to_dict(value, field_name, ctx, format)
            }
            Self::Uuid => uuid::uuid_dumper::dump_to_dict(value, field_name, ctx),
            Self::StrEnum(data) => {
                str_enum::str_enum_dumper::dump_to_dict(
                    value,
                    field_name,
                    ctx,
                    &data.enum_cls,
                    data.enum_name.as_deref(),
                    data.enum_members_repr.as_deref(),
                )
            }
            Self::IntEnum(data) => {
                str_enum::int_enum_dumper::dump_to_dict(
                    value,
                    field_name,
                    ctx,
                    &data.enum_cls,
                    data.enum_name.as_deref(),
                    data.enum_members_repr.as_deref(),
                )
            }
            Self::Any => any::any_dumper::dump_to_dict(ctx.py, value, field_name),
            Self::Collection(data) => {
                collection::collection_dumper::dump_to_dict(
                    value,
                    field_name,
                    ctx,
                    data.kind,
                    &data.item,
                    data.item_validator.as_ref(),
                )
            }
            Self::Dict(data) => {
                dict::dict_dumper::dump_to_dict(
                    value,
                    field_name,
                    ctx,
                    &data.value,
                    data.value_validator.as_ref(),
                )
            }
            Self::Nested { schema } => {
                nested::nested_dumper::dump_to_dict(value, field_name, ctx, schema)
            }
            Self::Union { variants } => {
                union::union_dumper::dump_to_dict(value, field_name, ctx, variants)
            }
        }
    }

    pub fn dump<S: serde::Serializer>(
        &self,
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, '_>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use crate::fields::{str_type, int, float, bool_type, decimal, date, time, datetime, uuid, str_enum, any, collection, dict, nested, union};

        match self {
            Self::Str { strip_whitespaces } => {
                str_type::str_dumper::dump(value, field_name, *strip_whitespaces, serializer)
            }
            Self::Int => int::int_dumper::dump(value, field_name, serializer),
            Self::Float => float::float_dumper::dump(value, field_name, serializer),
            Self::Bool => bool_type::bool_dumper::dump(value, field_name, serializer),
            Self::Decimal(data) => {
                decimal::decimal_dumper::dump(
                    value,
                    field_name,
                    ctx,
                    data.decimal_places,
                    data.rounding_strategy,
                    data.invalid_error.as_deref(),
                    serializer,
                )
            }
            Self::Date => date::date_dumper::dump(value, field_name, serializer),
            Self::Time => time::time_dumper::dump(value, field_name, serializer),
            Self::DateTime { format } => {
                datetime::datetime_dumper::dump(value, field_name, ctx, format, serializer)
            }
            Self::Uuid => uuid::uuid_dumper::dump(value, field_name, serializer),
            Self::StrEnum(data) => {
                str_enum::str_enum_dumper::dump(
                    value,
                    field_name,
                    ctx,
                    &data.enum_cls,
                    data.enum_name.as_deref(),
                    data.enum_members_repr.as_deref(),
                    serializer,
                )
            }
            Self::IntEnum(data) => {
                str_enum::int_enum_dumper::dump(
                    value,
                    field_name,
                    ctx,
                    &data.enum_cls,
                    data.enum_name.as_deref(),
                    data.enum_members_repr.as_deref(),
                    serializer,
                )
            }
            Self::Any => any::any_dumper::dump(value, field_name, serializer),
            Self::Collection(data) => {
                collection::collection_dumper::dump(
                    value,
                    field_name,
                    ctx,
                    data.kind,
                    &data.item,
                    data.item_validator.as_ref(),
                    serializer,
                )
            }
            Self::Dict(data) => {
                dict::dict_dumper::dump(
                    value,
                    field_name,
                    ctx,
                    &data.value,
                    data.value_validator.as_ref(),
                    serializer,
                )
            }
            Self::Nested { schema } => {
                nested::nested_dumper::dump(value, field_name, ctx, schema, serializer)
            }
            Self::Union { variants } => {
                union::union_dumper::dump(value, field_name, ctx, variants, serializer)
            }
        }
    }
}
