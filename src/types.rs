use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::PyString;
use pyo3::Borrowed;

use crate::loader::{Loader, FieldLoader};
use crate::dumper::{FieldDumper, Dumper};

pub struct DumpContext<'a, 'py> {
    pub py: Python<'py>,
    pub none_value_handling: Option<&'a str>,
    pub global_decimal_places: Option<i32>,
}

pub struct LoadContext<'py> {
    pub py: Python<'py>,
    pub decimal_places: Option<i32>,
}

impl<'py> LoadContext<'py> {
    pub const fn new(py: Python<'py>, decimal_places: Option<i32>) -> Self {
        Self { py, decimal_places }
    }
}

pub type DumpFn = for<'a, 'py> fn(
    value: &Bound<'py, PyAny>,
    field: Option<&FieldDescriptor>,
    ctx: &DumpContext<'a, 'py>,
) -> PyResult<Py<PyAny>>;

pub type DumpJsonFn = for<'a, 'py> fn(
    value: &Bound<'py, PyAny>,
    field: Option<&FieldDescriptor>,
    ctx: &DumpContext<'a, 'py>,
) -> Result<serde_json::Value, String>;

pub type LoadFn = for<'py> fn(
    value: &Bound<'py, PyAny>,
    field: &FieldDescriptor,
    ctx: &LoadContext<'py>,
) -> PyResult<Py<PyAny>>;


pub fn callback_required_dump<'py>(
    _value: &Bound<'py, PyAny>,
    _field: Option<&FieldDescriptor>,
    _ctx: &DumpContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Dump callback not configured"))
}

pub fn callback_required_dump_json<'py>(
    _value: &Bound<'py, PyAny>,
    _field: Option<&FieldDescriptor>,
    _ctx: &DumpContext<'_, 'py>,
) -> Result<serde_json::Value, String> {
    Err("Dump JSON callback not configured".to_string())
}

pub fn callback_required_load<'py>(
    _value: &Bound<'py, PyAny>,
    _field: &FieldDescriptor,
    _ctx: &LoadContext<'py>,
) -> PyResult<Py<PyAny>> {
    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Load callback not configured"))
}


#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DecimalPlaces {
    NotSpecified,
    NoRounding,
    Places(i32),
}

impl DecimalPlaces {
    #[inline]
    pub fn resolve(self, fallback: Option<i32>) -> Option<i32> {
        match self {
            Self::NoRounding => None,
            Self::Places(n) => Some(n),
            Self::NotSpecified => fallback.or(Some(2)),
        }
        .filter(|&p| p >= 0)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
#[repr(usize)]
pub enum FieldType {
    Str = 0,
    Int = 1,
    Float = 2,
    Bool = 3,
    Decimal = 4,
    Uuid = 5,
    DateTime = 6,
    Date = 7,
    Time = 8,
    List = 9,
    Dict = 10,
    Nested = 11,
    StrEnum = 12,
    IntEnum = 13,
    Set = 14,
    FrozenSet = 15,
    Tuple = 16,
    Union = 17,
    Any = 18,
}

impl FromPyObject<'_, '_> for FieldType {
    type Error = PyErr;

    fn extract(ob: Borrowed<'_, '_, PyAny>) -> Result<Self, Self::Error> {
        let s: &str = ob.extract()?;
        Self::from_str(s).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Unknown field type: {s}"))
        })
    }
}

impl FieldType {
    pub fn from_str(s: &str) -> Option<Self> {
        Some(match s {
            "str" => Self::Str,
            "int" => Self::Int,
            "float" => Self::Float,
            "bool" => Self::Bool,
            "decimal" => Self::Decimal,
            "uuid" => Self::Uuid,
            "datetime" => Self::DateTime,
            "date" => Self::Date,
            "time" => Self::Time,
            "list" => Self::List,
            "dict" => Self::Dict,
            "nested" => Self::Nested,
            "str_enum" => Self::StrEnum,
            "int_enum" => Self::IntEnum,
            "set" => Self::Set,
            "frozenset" => Self::FrozenSet,
            "tuple" => Self::Tuple,
            "union" => Self::Union,
            "any" => Self::Any,
            _ => return None,
        })
    }

}

#[allow(clippy::struct_excessive_bools)]
pub struct FieldDescriptor {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub data_key: Option<String>,
    pub field_type: FieldType,
    pub dump_fn: DumpFn,
    pub dump_json_fn: DumpJsonFn,
    pub load_fn: LoadFn,
    pub optional: bool,
    pub slot_offset: Option<isize>,
    pub nested_schema: Option<Box<SchemaDescriptor>>,
    pub item_schema: Option<Box<Self>>,
    pub value_schema: Option<Box<Self>>,
    pub strip_whitespaces: bool,
    pub decimal_places: DecimalPlaces,
    pub decimal_rounding: Option<Py<PyAny>>,
    pub datetime_format: Option<String>,
    pub enum_cls: Option<Py<PyAny>>,
    pub str_enum_values: Option<Vec<(String, Py<PyAny>)>>,
    pub int_enum_values: Option<Vec<(i64, Py<PyAny>)>>,
    pub enum_name: Option<String>,
    pub enum_members_repr: Option<String>,
    pub union_variants: Option<Vec<Self>>,
    pub default_value: Option<Py<PyAny>>,
    pub default_factory: Option<Py<PyAny>>,
    pub required_error: Option<String>,
    pub none_error: Option<String>,
    pub invalid_error: Option<String>,
    pub field_init: bool,
    pub post_load: Option<Py<PyAny>>,
    pub validator: Option<Py<PyAny>>,
    pub item_validator: Option<Py<PyAny>>,
    pub value_validator: Option<Py<PyAny>>,
}

impl std::fmt::Debug for FieldDescriptor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FieldDescriptor")
            .field("name", &self.name)
            .field("field_type", &self.field_type)
            .field("optional", &self.optional)
            .finish_non_exhaustive()
    }
}

impl Clone for FieldDescriptor {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            name: self.name.clone(),
            name_interned: self.name_interned.clone_ref(py),
            data_key: self.data_key.clone(),
            field_type: self.field_type,
            dump_fn: self.dump_fn,
            dump_json_fn: self.dump_json_fn,
            load_fn: self.load_fn,
            optional: self.optional,
            slot_offset: self.slot_offset,
            nested_schema: self.nested_schema.clone(),
            item_schema: self.item_schema.clone(),
            value_schema: self.value_schema.clone(),
            strip_whitespaces: self.strip_whitespaces,
            decimal_places: self.decimal_places,
            decimal_rounding: self.decimal_rounding.as_ref().map(|r| r.clone_ref(py)),
            datetime_format: self.datetime_format.clone(),
            enum_cls: self.enum_cls.as_ref().map(|c| c.clone_ref(py)),
            str_enum_values: self.str_enum_values.as_ref().map(|v| {
                v.iter().map(|(k, val)| (k.clone(), val.clone_ref(py))).collect()
            }),
            int_enum_values: self.int_enum_values.as_ref().map(|v| {
                v.iter().map(|(k, val)| (*k, val.clone_ref(py))).collect()
            }),
            enum_name: self.enum_name.clone(),
            enum_members_repr: self.enum_members_repr.clone(),
            union_variants: self.union_variants.clone(),
            default_value: self.default_value.as_ref().map(|v| v.clone_ref(py)),
            default_factory: self.default_factory.as_ref().map(|f| f.clone_ref(py)),
            required_error: self.required_error.clone(),
            none_error: self.none_error.clone(),
            invalid_error: self.invalid_error.clone(),
            field_init: self.field_init,
            post_load: self.post_load.as_ref().map(|v| v.clone_ref(py)),
            validator: self.validator.as_ref().map(|v| v.clone_ref(py)),
            item_validator: self.item_validator.as_ref().map(|v| v.clone_ref(py)),
            value_validator: self.value_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

impl FromPyObject<'_, '_> for FieldDescriptor {
    type Error = PyErr;

    fn extract(ob: Borrowed<'_, '_, PyAny>) -> Result<Self, Self::Error> {
        let py = ob.py();
        let name: String = ob.getattr("name")?.extract()?;
        let name_interned = PyString::intern(py, &name).unbind();
        let data_key: Option<String> = ob.getattr("data_key")?.extract()?;
        let field_type: FieldType = ob.getattr("field_type")?.extract()?;
        let optional: bool = ob.getattr("optional")?.extract()?;
        let slot_offset: Option<isize> = ob.getattr("slot_offset")?.extract().ok().flatten()
            .filter(|&offset: &isize| offset.cast_unsigned().is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()));

        let nested_schema: Option<SchemaDescriptor> = ob.getattr("nested_schema")?.extract()?;
        let item_schema: Option<Self> = ob.getattr("item_schema")?.extract()?;
        let value_schema: Option<Self> = ob.getattr("value_schema")?.extract()?;

        let strip_whitespaces: bool = ob.getattr("strip_whitespaces")?.extract().unwrap_or(false);
        let decimal_places = {
            let attr = ob.getattr("decimal_places")?;
            if attr.is_none() {
                DecimalPlaces::NoRounding
            } else if let Ok(v) = attr.extract::<i32>() {
                DecimalPlaces::Places(v)
            } else {
                DecimalPlaces::NotSpecified
            }
        };
        let decimal_rounding: Option<Py<PyAny>> = ob.getattr("decimal_rounding")?.extract().ok();
        let datetime_format: Option<String> = ob.getattr("datetime_format")?.extract().ok().flatten();
        let required_error: Option<String> = ob.getattr("required_error")?.extract().ok().flatten();
        let none_error: Option<String> = ob.getattr("none_error")?.extract().ok().flatten();
        let invalid_error: Option<String> = ob.getattr("invalid_error")?.extract().ok().flatten();
        let enum_cls: Option<Py<PyAny>> = ob.getattr("enum_cls")?.extract().ok();
        let union_variants: Option<Vec<Self>> = ob.getattr("union_variants")?.extract().ok();

        let default_value: Option<Py<PyAny>> = ob.getattr("default_value")?.extract().ok();
        let default_factory: Option<Py<PyAny>> = ob.getattr("default_factory")?.extract().ok();
        let field_init: bool = ob.getattr("field_init")?.extract().unwrap_or(true);

        Ok(Self {
            name,
            name_interned,
            data_key,
            dump_fn: callback_required_dump,
            dump_json_fn: callback_required_dump_json,
            load_fn: callback_required_load,
            field_type,
            optional,
            slot_offset,
            nested_schema: nested_schema.map(Box::new),
            item_schema: item_schema.map(Box::new),
            value_schema: value_schema.map(Box::new),
            strip_whitespaces,
            decimal_places,
            decimal_rounding,
            datetime_format,
            enum_cls,
            str_enum_values: None,
            int_enum_values: None,
            enum_name: None,
            enum_members_repr: None,
            union_variants,
            default_value,
            default_factory,
            required_error,
            none_error,
            invalid_error,
            field_init,
            post_load: None,
            validator: None,
            item_validator: None,
            value_validator: None,
        })
    }
}

#[derive(Debug)]
pub struct SchemaDescriptor {
    pub cls: Py<PyAny>,
    pub fields: Vec<FieldDescriptor>,
    pub field_lookup: HashMap<String, usize>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
    pub dumper_fields: Option<Vec<FieldDumper>>,
    pub loader_fields: Option<Vec<FieldLoader>>,
}

impl Clone for SchemaDescriptor {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
            dumper_fields: self.dumper_fields.clone(),
            loader_fields: self.loader_fields.clone(),
        })
    }
}

impl FromPyObject<'_, '_> for SchemaDescriptor {
    type Error = PyErr;

    fn extract(ob: Borrowed<'_, '_, PyAny>) -> Result<Self, Self::Error> {
        let cls: Py<PyAny> = ob.getattr("cls")?.extract()?;
        let fields: Vec<FieldDescriptor> = ob.getattr("fields")?.extract()?;
        let can_use_direct_slots: bool = ob.getattr("can_use_direct_slots")?.extract().unwrap_or(false);
        let has_post_init: bool = ob.getattr("has_post_init")?.extract().unwrap_or(false);
        let field_lookup = build_field_lookup(&fields);
        Ok(Self { cls, fields, field_lookup, can_use_direct_slots, has_post_init, dumper_fields: None, loader_fields: None })
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum TypeKind {
    Dataclass,
    Primitive,
    List,
    Dict,
    Optional,
    Set,
    FrozenSet,
    Tuple,
    Union,
}

impl FromPyObject<'_, '_> for TypeKind {
    type Error = PyErr;

    fn extract(ob: Borrowed<'_, '_, PyAny>) -> Result<Self, Self::Error> {
        let s: &str = ob.extract()?;
        Self::from_str(s).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Unknown type kind: {s}"))
        })
    }
}

impl TypeKind {
    fn from_str(s: &str) -> Option<Self> {
        Some(match s {
            "dataclass" => Self::Dataclass,
            "primitive" => Self::Primitive,
            "list" => Self::List,
            "dict" => Self::Dict,
            "optional" => Self::Optional,
            "set" => Self::Set,
            "frozenset" => Self::FrozenSet,
            "tuple" => Self::Tuple,
            "union" => Self::Union,
            _ => return None,
        })
    }
}

#[derive(Debug)]
pub struct TypeDescriptor {
    pub type_kind: TypeKind,
    pub primitive_type: Option<FieldType>,
    pub primitive_dump_fn: Option<DumpFn>,
    pub primitive_dump_json_fn: Option<DumpJsonFn>,
    pub primitive_dumper: Option<Dumper>,
    pub primitive_loader: Option<Loader>,
    pub optional: bool,
    pub inner_type: Option<Box<Self>>,
    pub item_type: Option<Box<Self>>,
    pub value_type: Option<Box<Self>>,
    pub cls: Option<Py<PyAny>>,
    pub fields: Vec<FieldDescriptor>,
    pub field_lookup: HashMap<String, usize>,
    pub union_variants: Option<Vec<Self>>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
    pub dumper_fields: Option<Vec<FieldDumper>>,
    pub loader_fields: Option<Vec<FieldLoader>>,
}

impl Clone for TypeDescriptor {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            type_kind: self.type_kind.clone(),
            primitive_type: self.primitive_type,
            primitive_dump_fn: self.primitive_dump_fn,
            primitive_dump_json_fn: self.primitive_dump_json_fn,
            primitive_dumper: self.primitive_dumper.clone(),
            primitive_loader: self.primitive_loader.clone(),
            optional: self.optional,
            inner_type: self.inner_type.clone(),
            item_type: self.item_type.clone(),
            value_type: self.value_type.clone(),
            cls: self.cls.as_ref().map(|c| c.clone_ref(py)),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            union_variants: self.union_variants.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
            dumper_fields: self.dumper_fields.clone(),
            loader_fields: self.loader_fields.clone(),
        })
    }
}

impl FromPyObject<'_, '_> for TypeDescriptor {
    type Error = PyErr;

    fn extract(ob: Borrowed<'_, '_, PyAny>) -> Result<Self, Self::Error> {
        let type_kind: TypeKind = ob.getattr("type_kind")?.extract()?;
        let primitive_type: Option<FieldType> = ob.getattr("primitive_type")?.extract().ok();
        let optional: bool = ob.getattr("optional")?.extract()?;
        let inner_type: Option<Self> = ob.getattr("inner_type")?.extract().ok();
        let item_type: Option<Self> = ob.getattr("item_type")?.extract().ok();
        let value_type: Option<Self> = ob.getattr("value_type")?.extract().ok();
        let cls: Option<Py<PyAny>> = ob.getattr("cls")?.extract().ok();
        let fields: Vec<FieldDescriptor> = ob.getattr("fields")?.extract().unwrap_or_default();
        let union_variants: Option<Vec<Self>> = ob.getattr("union_variants")?.extract().ok();
        let can_use_direct_slots: bool = ob.getattr("can_use_direct_slots")?.extract().unwrap_or(false);
        let has_post_init: bool = ob.getattr("has_post_init")?.extract().unwrap_or(false);
        let field_lookup = build_field_lookup(&fields);

        Ok(Self {
            type_kind,
            primitive_type,
            primitive_dump_fn: None,
            primitive_dump_json_fn: None,
            primitive_dumper: None,
            primitive_loader: None,
            optional,
            inner_type: inner_type.map(Box::new),
            item_type: item_type.map(Box::new),
            value_type: value_type.map(Box::new),
            cls,
            fields,
            field_lookup,
            union_variants,
            can_use_direct_slots,
            has_post_init,
            dumper_fields: None,
            loader_fields: None,
        })
    }
}

pub fn build_field_lookup(fields: &[FieldDescriptor]) -> HashMap<String, usize> {
    fields.iter().enumerate()
        .map(|(idx, field)| (field.data_key.as_ref().unwrap_or(&field.name).clone(), idx))
        .collect()
}
