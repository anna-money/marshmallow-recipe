#![allow(clippy::struct_field_names)]

use pyo3::prelude::*;
use rust_decimal::RoundingStrategy;

pub use crate::fields::collection::CollectionKind;
pub use crate::fields::nested::{DataclassLoaderSchema, FieldLoader};
use crate::types::{DecimalPlaces, LoadContext};

pub use crate::fields::nested::nested_loader::load_dataclass_from_parts;

pub struct StrEnumLoaderData {
    pub values: Vec<(String, Py<PyAny>)>,
}

impl Clone for StrEnumLoaderData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            values: self.values.iter().map(|(k, v)| (k.clone(), v.clone_ref(py))).collect(),
        })
    }
}

pub struct IntEnumLoaderData {
    pub values: Vec<(i64, Py<PyAny>)>,
}

impl Clone for IntEnumLoaderData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            values: self.values.iter().map(|(k, v)| (*k, v.clone_ref(py))).collect(),
        })
    }
}

#[derive(Clone, Copy)]
pub struct DecimalLoaderData {
    pub decimal_places: DecimalPlaces,
    pub rounding_strategy: Option<RoundingStrategy>,
}

pub struct CollectionLoaderData {
    pub item: Box<Loader>,
    pub kind: CollectionKind,
    pub item_validator: Option<Py<PyAny>>,
}

impl Clone for CollectionLoaderData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            item: self.item.clone(),
            kind: self.kind,
            item_validator: self.item_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

pub struct DictLoaderData {
    pub value: Box<Loader>,
    pub value_validator: Option<Py<PyAny>>,
}

impl Clone for DictLoaderData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            value: self.value.clone(),
            value_validator: self.value_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

impl std::fmt::Debug for Loader {
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
pub enum Loader {
    Str { strip_whitespaces: bool },
    Int,
    Float,
    Bool,
    Decimal(Box<DecimalLoaderData>),
    Date,
    Time,
    DateTime { format: Option<String> },
    Uuid,
    StrEnum(Box<StrEnumLoaderData>),
    IntEnum(Box<IntEnumLoaderData>),
    Any,
    Collection(Box<CollectionLoaderData>),
    Dict(Box<DictLoaderData>),
    Nested { schema: Box<DataclassLoaderSchema> },
    Union { variants: Vec<Self> },
}

impl Loader {
    pub fn load_from_dict<'py>(
        &self,
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        use crate::fields::{str_type, int, float, bool_type, decimal, date, time, datetime, uuid, str_enum, int_enum, any, collection, dict, nested, union};

        match self {
            Self::Str { strip_whitespaces } => {
                str_type::str_loader::load_from_dict(value, field_name, invalid_error, ctx, *strip_whitespaces)
            }
            Self::Int => int::int_loader::load_from_dict(value, field_name, invalid_error, ctx),
            Self::Float => float::float_loader::load_from_dict(value, field_name, invalid_error, ctx),
            Self::Bool => bool_type::bool_loader::load_from_dict(value, field_name, invalid_error, ctx),
            Self::Decimal(data) => {
                decimal::decimal_loader::load_from_dict(
                    value,
                    field_name,
                    invalid_error,
                    ctx,
                    data.decimal_places,
                    data.rounding_strategy,
                )
            }
            Self::Date => date::date_loader::load_from_dict(value, field_name, invalid_error, ctx),
            Self::Time => time::time_loader::load_from_dict(value, field_name, invalid_error, ctx),
            Self::DateTime { format } => {
                datetime::datetime_loader::load_from_dict(value, field_name, invalid_error, ctx, format.as_deref())
            }
            Self::Uuid => uuid::uuid_loader::load_from_dict(value, field_name, invalid_error, ctx),
            Self::StrEnum(data) => {
                str_enum::str_enum_loader::load_from_dict(value, field_name, ctx, &data.values)
            }
            Self::IntEnum(data) => {
                int_enum::int_enum_loader::load_from_dict(value, field_name, ctx, &data.values)
            }
            Self::Any => any::any_loader::load_from_dict(value, ctx),
            Self::Collection(data) => {
                collection::collection_loader::load_from_dict(
                    value,
                    field_name,
                    invalid_error,
                    ctx,
                    data.kind,
                    &data.item,
                    data.item_validator.as_ref(),
                )
            }
            Self::Dict(data) => {
                dict::dict_loader::load_from_dict(
                    value,
                    field_name,
                    invalid_error,
                    ctx,
                    &data.value,
                    data.value_validator.as_ref(),
                )
            }
            Self::Nested { schema } => {
                nested::nested_loader::load_from_dict(value, field_name, invalid_error, ctx, schema)
            }
            Self::Union { variants } => {
                union::union_loader::load_from_dict(value, field_name, invalid_error, ctx, variants)
            }
        }
    }
}
