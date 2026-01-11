use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::PyString;
use pyo3::Borrowed;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FieldType {
    Str,
    Int,
    Float,
    Bool,
    Decimal,
    Uuid,
    DateTime,
    Date,
    Time,
    List,
    Dict,
    Nested,
    StrEnum,
    IntEnum,
    Set,
    FrozenSet,
    Tuple,
    Union,
    Any,
}

impl FromPyObject<'_, '_> for FieldType {
    type Error = PyErr;

    fn extract(ob: Borrowed<'_, '_, PyAny>) -> Result<Self, Self::Error> {
        let s: String = ob.extract()?;
        match s.as_str() {
            "str" => Ok(Self::Str),
            "int" => Ok(Self::Int),
            "float" => Ok(Self::Float),
            "bool" => Ok(Self::Bool),
            "decimal" => Ok(Self::Decimal),
            "uuid" => Ok(Self::Uuid),
            "datetime" => Ok(Self::DateTime),
            "date" => Ok(Self::Date),
            "time" => Ok(Self::Time),
            "list" => Ok(Self::List),
            "dict" => Ok(Self::Dict),
            "nested" => Ok(Self::Nested),
            "str_enum" => Ok(Self::StrEnum),
            "int_enum" => Ok(Self::IntEnum),
            "set" => Ok(Self::Set),
            "frozenset" => Ok(Self::FrozenSet),
            "tuple" => Ok(Self::Tuple),
            "union" => Ok(Self::Union),
            "any" => Ok(Self::Any),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Unknown field type: {s}"),
            )),
        }
    }
}

#[derive(Debug)]
#[allow(clippy::struct_excessive_bools)]
pub struct FieldDescriptor {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub serialized_name: Option<String>,
    pub field_type: FieldType,
    pub optional: bool,
    pub slot_offset: Option<isize>,
    pub nested_schema: Option<Box<SchemaDescriptor>>,
    pub item_schema: Option<Box<Self>>,
    pub key_type: Option<FieldType>,
    pub value_schema: Option<Box<Self>>,
    pub strip_whitespaces: bool,
    pub decimal_places: Option<i32>,
    pub decimal_as_string: bool,
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
    pub validator: Option<Py<PyAny>>,
    pub item_validator: Option<Py<PyAny>>,
    pub value_validator: Option<Py<PyAny>>,
}

impl Clone for FieldDescriptor {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            name: self.name.clone(),
            name_interned: self.name_interned.clone_ref(py),
            serialized_name: self.serialized_name.clone(),
            field_type: self.field_type.clone(),
            optional: self.optional,
            slot_offset: self.slot_offset,
            nested_schema: self.nested_schema.clone(),
            item_schema: self.item_schema.clone(),
            key_type: self.key_type.clone(),
            value_schema: self.value_schema.clone(),
            strip_whitespaces: self.strip_whitespaces,
            decimal_places: self.decimal_places,
            decimal_as_string: self.decimal_as_string,
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
        let serialized_name: Option<String> = ob.getattr("serialized_name")?.extract()?;
        let field_type: FieldType = ob.getattr("field_type")?.extract()?;
        let optional: bool = ob.getattr("optional")?.extract()?;
        // slot_offset is used for direct memory access to Python object slots.
        // We only use it if the offset is properly aligned for pointer access.
        // Unaligned offsets can occur if a dataclass inherits from a C extension
        // with a misaligned tp_basicsize (see CPython issue #129675).
        // If unaligned, we fall back to regular getattr access.
        let slot_offset: Option<isize> = ob.getattr("slot_offset")?.extract().ok().flatten()
            .filter(|&offset: &isize| offset.cast_unsigned().is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()));

        let nested_schema: Option<SchemaDescriptor> = ob.getattr("nested_schema")?.extract()?;
        let item_schema: Option<Self> = ob.getattr("item_schema")?.extract()?;
        let key_type: Option<FieldType> = ob.getattr("key_type")?.extract()?;
        let value_schema: Option<Self> = ob.getattr("value_schema")?.extract()?;

        let strip_whitespaces: bool = ob.getattr("strip_whitespaces")?.extract().unwrap_or(false);
        let decimal_places: Option<i32> = ob.getattr("decimal_places")?.extract().ok().flatten();
        let decimal_as_string: bool = ob.getattr("decimal_as_string")?.extract().unwrap_or(true);
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
            serialized_name,
            field_type,
            optional,
            slot_offset,
            nested_schema: nested_schema.map(Box::new),
            item_schema: item_schema.map(Box::new),
            key_type,
            value_schema: value_schema.map(Box::new),
            strip_whitespaces,
            decimal_places,
            decimal_as_string,
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
}

impl Clone for SchemaDescriptor {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
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
        Ok(Self { cls, fields, field_lookup, can_use_direct_slots, has_post_init })
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
        let s: String = ob.extract()?;
        match s.as_str() {
            "dataclass" => Ok(Self::Dataclass),
            "primitive" => Ok(Self::Primitive),
            "list" => Ok(Self::List),
            "dict" => Ok(Self::Dict),
            "optional" => Ok(Self::Optional),
            "set" => Ok(Self::Set),
            "frozenset" => Ok(Self::FrozenSet),
            "tuple" => Ok(Self::Tuple),
            "union" => Ok(Self::Union),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Unknown type kind: {s}"),
            )),
        }
    }
}

#[derive(Debug)]
pub struct TypeDescriptor {
    pub type_kind: TypeKind,
    pub primitive_type: Option<FieldType>,
    pub optional: bool,
    pub inner_type: Option<Box<Self>>,
    pub item_type: Option<Box<Self>>,
    pub key_type: Option<FieldType>,
    pub value_type: Option<Box<Self>>,
    pub cls: Option<Py<PyAny>>,
    pub fields: Vec<FieldDescriptor>,
    pub field_lookup: HashMap<String, usize>,
    pub union_variants: Option<Vec<Self>>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
}

impl Clone for TypeDescriptor {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            type_kind: self.type_kind.clone(),
            primitive_type: self.primitive_type.clone(),
            optional: self.optional,
            inner_type: self.inner_type.clone(),
            item_type: self.item_type.clone(),
            key_type: self.key_type.clone(),
            value_type: self.value_type.clone(),
            cls: self.cls.as_ref().map(|c| c.clone_ref(py)),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            union_variants: self.union_variants.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
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
        let key_type: Option<FieldType> = ob.getattr("key_type")?.extract().ok();
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
            optional,
            inner_type: inner_type.map(Box::new),
            item_type: item_type.map(Box::new),
            key_type,
            value_type: value_type.map(Box::new),
            cls,
            fields,
            field_lookup,
            union_variants,
            can_use_direct_slots,
            has_post_init,
        })
    }
}

fn build_field_lookup(fields: &[FieldDescriptor]) -> HashMap<String, usize> {
    let mut lookup = HashMap::with_capacity(fields.len());
    for (idx, field) in fields.iter().enumerate() {
        let key = field.serialized_name.as_ref().unwrap_or(&field.name).clone();
        lookup.insert(key, idx);
    }
    lookup
}
