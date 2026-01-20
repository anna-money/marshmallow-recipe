#![allow(clippy::struct_field_names)]

use pyo3::prelude::*;

pub use crate::field_types::collection::CollectionKind;
pub use crate::field_types::nested::{DataclassDeserializerSchema, FieldDeserializer};
use crate::types::{DecimalPlaces, LoadContext};

pub use crate::field_types::nested::nested_deserializer::deserialize_dataclass_from_parts;

pub struct StrEnumDeserData {
    pub values: Vec<(String, Py<PyAny>)>,
}

impl Clone for StrEnumDeserData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            values: self.values.iter().map(|(k, v)| (k.clone(), v.clone_ref(py))).collect(),
        })
    }
}

pub struct IntEnumDeserData {
    pub values: Vec<(i64, Py<PyAny>)>,
}

impl Clone for IntEnumDeserData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            values: self.values.iter().map(|(k, v)| (*k, v.clone_ref(py))).collect(),
        })
    }
}

pub struct DecimalDeserData {
    pub decimal_places: DecimalPlaces,
    pub decimal_rounding: Option<Py<PyAny>>,
}

impl Clone for DecimalDeserData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            decimal_places: self.decimal_places,
            decimal_rounding: self.decimal_rounding.as_ref().map(|r| r.clone_ref(py)),
        })
    }
}

pub struct CollectionDeserData {
    pub item: Box<Deserializer>,
    pub kind: CollectionKind,
    pub item_validator: Option<Py<PyAny>>,
}

impl Clone for CollectionDeserData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            item: self.item.clone(),
            kind: self.kind,
            item_validator: self.item_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

pub struct DictDeserData {
    pub value: Box<Deserializer>,
    pub value_validator: Option<Py<PyAny>>,
}

impl Clone for DictDeserData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            value: self.value.clone(),
            value_validator: self.value_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

impl std::fmt::Debug for Deserializer {
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
pub enum Deserializer {
    Str { strip_whitespaces: bool },
    Int,
    Float,
    Bool,
    Decimal(Box<DecimalDeserData>),
    Date,
    Time,
    DateTime { format: Option<String> },
    Uuid,
    StrEnum(Box<StrEnumDeserData>),
    IntEnum(Box<IntEnumDeserData>),
    Any,
    Collection(Box<CollectionDeserData>),
    Dict(Box<DictDeserData>),
    Nested { schema: Box<DataclassDeserializerSchema> },
    Union { variants: Vec<Self> },
}

impl Deserializer {
    pub fn deserialize_from_dict<'py>(
        &self,
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        use crate::field_types::{str_type, int, float, bool_type, decimal, date, time, datetime, uuid, str_enum, int_enum, any, collection, dict, nested, union};

        match self {
            Self::Str { strip_whitespaces } => {
                str_type::str_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx, *strip_whitespaces)
            }
            Self::Int => int::int_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx),
            Self::Float => float::float_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx),
            Self::Bool => bool_type::bool_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx),
            Self::Decimal(data) => {
                decimal::decimal_deserializer::deserialize_from_dict(
                    value,
                    field_name,
                    invalid_error,
                    ctx,
                    data.decimal_places,
                    data.decimal_rounding.as_ref(),
                )
            }
            Self::Date => date::date_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx),
            Self::Time => time::time_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx),
            Self::DateTime { format } => {
                datetime::datetime_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx, format.as_deref())
            }
            Self::Uuid => uuid::uuid_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx),
            Self::StrEnum(data) => {
                str_enum::str_enum_deserializer::deserialize_from_dict(value, field_name, ctx, &data.values)
            }
            Self::IntEnum(data) => {
                int_enum::int_enum_deserializer::deserialize_from_dict(value, field_name, ctx, &data.values)
            }
            Self::Any => any::any_deserializer::deserialize_from_dict(value, ctx),
            Self::Collection(data) => {
                collection::collection_deserializer::deserialize_from_dict(
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
                dict::dict_deserializer::deserialize_from_dict(
                    value,
                    field_name,
                    invalid_error,
                    ctx,
                    &data.value,
                    data.value_validator.as_ref(),
                )
            }
            Self::Nested { schema } => {
                nested::nested_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx, schema)
            }
            Self::Union { variants } => {
                union::union_deserializer::deserialize_from_dict(value, field_name, invalid_error, ctx, variants)
            }
        }
    }
}
