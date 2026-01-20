use once_cell::sync::{Lazy, OnceCell};
use pyo3::ffi;
use pyo3::prelude::*;
use pyo3::types::{PyDelta, PyDict, PyList, PyString, PyTuple};
use std::collections::HashMap;
use std::sync::RwLock;

use crate::types::{
    DecimalPlaces, FieldDescriptor, FieldType, SchemaDescriptor, TypeDescriptor, TypeKind, build_field_lookup,
    callback_required_serialize, callback_required_serialize_json, callback_required_deserialize,
};
use crate::serializer::{
    Serializer, FieldSerializer, DataclassSerializerSchema,
    CollectionData, CollectionKind, DictData,
    StrEnumData, IntEnumData, DecimalData as SerDecimalData,
};
use crate::deserializer::{
    Deserializer, FieldDeserializer, DataclassDeserializerSchema,
    CollectionDeserData, DictDeserData,
    StrEnumDeserData, IntEnumDeserData, DecimalDeserData,
};

pub static SCHEMA_CACHE: Lazy<RwLock<HashMap<u64, TypeDescriptor>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));

pub struct CachedPyTypes {
    pub int_cls: Py<PyAny>,
    pub decimal_cls: Py<PyAny>,
    pub uuid_cls: Py<PyAny>,
    pub timezone_cls: Py<PyAny>,
    pub utc_tz: Py<PyAny>,
    pub object_cls: Py<PyAny>,
    pub str_new: Py<PyString>,
    pub str_int: Py<PyString>,
    pub str_utcoffset: Py<PyString>,
    pub missing_sentinel: Py<PyAny>,
    pub timezones: Vec<Py<PyAny>>,
}

impl CachedPyTypes {
    pub fn create_uuid_fast(&self, py: Python, uuid_int: u128) -> PyResult<Py<PyAny>> {
        let int_obj = uuid_int.into_pyobject(py)?;
        let none = unsafe { ffi::Py_None() };
        let args: [*mut ffi::PyObject; 5] = [none, none, none, none, int_obj.as_ptr()];
        let result = unsafe {
            ffi::PyObject_Vectorcall(self.uuid_cls.as_ptr(), args.as_ptr(), 5, std::ptr::null_mut())
        };
        if result.is_null() {
            Err(PyErr::fetch(py))
        } else {
            Ok(unsafe { Py::from_owned_ptr(py, result) })
        }
    }

    pub fn get_timezone(&self, py: Python, offset_seconds: i32) -> PyResult<Py<PyAny>> {
        if offset_seconds == 0 {
            return Ok(self.utc_tz.clone_ref(py));
        }

        if offset_seconds % 1800 == 0 {
            let half_hours = offset_seconds / 1800 + 24;
            if let Some(index) = usize::try_from(half_hours).ok().filter(|&i| i < 53) {
                if let Some(tz) = self.timezones.get(index) {
                    return Ok(tz.clone_ref(py));
                }
            }
        }

        let py_delta = PyDelta::new(py, 0, offset_seconds, 0, true)?;
        self.timezone_cls.bind(py).call1((py_delta,)).map(Bound::unbind)
    }
}

fn build_timezone_cache(py: Python, timezone_cls: &Bound<'_, PyAny>) -> PyResult<Vec<Py<PyAny>>> {
    let mut cache = Vec::with_capacity(53);
    for half_hours in -24..=28 {
        let offset = half_hours * 1800;
        let py_delta = PyDelta::new(py, 0, offset, 0, true)?;
        let tz = timezone_cls.call1((py_delta,))?.unbind();
        cache.push(tz);
    }
    Ok(cache)
}

static CACHED_PY_TYPES: OnceCell<CachedPyTypes> = OnceCell::new();

pub fn get_cached_types(py: Python) -> PyResult<&'static CachedPyTypes> {
    CACHED_PY_TYPES.get_or_try_init(|| {
        let decimal_mod = py.import("decimal")?;
        let uuid_mod = py.import("uuid")?;
        let datetime_mod = py.import("datetime")?;
        let builtins = py.import("builtins")?;
        let mr_missing_mod = py.import("marshmallow_recipe.missing")?;

        let timezone_cls = datetime_mod.getattr("timezone")?;
        let timezones = build_timezone_cache(py, &timezone_cls)?;

        Ok(CachedPyTypes {
            int_cls: builtins.getattr("int")?.unbind(),
            decimal_cls: decimal_mod.getattr("Decimal")?.unbind(),
            uuid_cls: uuid_mod.getattr("UUID")?.unbind(),
            timezone_cls: timezone_cls.unbind(),
            utc_tz: datetime_mod.getattr("UTC")?.unbind(),
            object_cls: builtins.getattr("object")?.unbind(),
            str_new: PyString::intern(py, "__new__").unbind(),
            str_int: PyString::intern(py, "int").unbind(),
            str_utcoffset: PyString::intern(py, "utcoffset").unbind(),
            missing_sentinel: mr_missing_mod.getattr("MISSING")?.unbind(),
            timezones,
        })
    })
}

#[pyfunction]
#[pyo3(signature = (schema_id, raw_schema))]
pub fn register(_py: Python, schema_id: u64, raw_schema: &Bound<'_, PyDict>) -> PyResult<()> {
    let descriptor = build_type_descriptor_from_dict(raw_schema)?;
    SCHEMA_CACHE.write().unwrap_or_else(std::sync::PoisonError::into_inner).insert(schema_id, descriptor);
    Ok(())
}

#[allow(clippy::too_many_lines)]
pub fn build_type_descriptor_from_dict(raw: &Bound<'_, PyDict>) -> PyResult<TypeDescriptor> {
    let type_kind: String = raw.get_item("type_kind")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing type_kind")
    })?.extract()?;

    match type_kind.as_str() {
        "dataclass" => {
            let fields_raw: Vec<Bound<'_, PyDict>> = raw.get_item("fields")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing fields")
            })?.extract()?;

            let cls: Py<PyAny> = raw.get_item("cls")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing cls")
            })?.extract()?;

            let fields: Vec<FieldDescriptor> = fields_raw
                .iter()
                .map(|f| build_field_from_dict(f))
                .collect::<PyResult<_>>()?;

            let can_use_direct_slots: bool = raw.get_item("can_use_direct_slots")?
                .is_some_and(|v| v.extract().unwrap_or(false));

            let has_post_init: bool = raw.get_item("has_post_init")?
                .is_some_and(|v| v.extract().unwrap_or(false));

            let py = raw.py();
            let field_lookup = build_field_lookup(&fields);
            let serializer_fields = build_serializer_fields(py, &fields);
            let deserializer_fields = build_deserializer_fields(py, &fields);
            Ok(TypeDescriptor {
                type_kind: TypeKind::Dataclass,
                primitive_type: None,
                primitive_serialize_fn: None,
                primitive_serialize_json_fn: None,
                primitive_serializer: None,
                primitive_deserializer: None,
                optional: false,
                inner_type: None,
                item_type: None,
                value_type: None,
                cls: Some(cls),
                fields,
                field_lookup,
                union_variants: None,
                can_use_direct_slots,
                has_post_init,
                serializer_fields: Some(serializer_fields),
                deserializer_fields: Some(deserializer_fields),
            })
        }
        "primitive" => {
            let primitive_type: String = raw.get_item("primitive_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_type")
            })?.extract()?;

            let parsed_type = parse_field_type(&primitive_type)?;
            let primitive_serializer = build_primitive_serializer(parsed_type);
            let primitive_deserializer = build_primitive_deserializer(parsed_type);
            Ok(TypeDescriptor {
                primitive_type: Some(parsed_type),
                primitive_serializer: Some(primitive_serializer),
                primitive_deserializer: Some(primitive_deserializer),
                ..default_type_descriptor(TypeKind::Primitive)
            })
        }
        "list" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                item_type: Some(Box::new(item_type)),
                ..default_type_descriptor(TypeKind::List)
            })
        }
        "dict" => {
            let value_raw: Bound<'_, PyDict> = raw.get_item("value_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type")
            })?.extract()?;
            let value_type = build_type_descriptor_from_dict(&value_raw)?;

            Ok(TypeDescriptor {
                value_type: Some(Box::new(value_type)),
                ..default_type_descriptor(TypeKind::Dict)
            })
        }
        "optional" => {
            let inner_raw: Bound<'_, PyDict> = raw.get_item("inner_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type")
            })?.extract()?;
            let inner_type = build_type_descriptor_from_dict(&inner_raw)?;

            Ok(TypeDescriptor {
                optional: true,
                inner_type: Some(Box::new(inner_type)),
                ..default_type_descriptor(TypeKind::Optional)
            })
        }
        "set" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for set")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                item_type: Some(Box::new(item_type)),
                ..default_type_descriptor(TypeKind::Set)
            })
        }
        "frozenset" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for frozenset")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                item_type: Some(Box::new(item_type)),
                ..default_type_descriptor(TypeKind::FrozenSet)
            })
        }
        "tuple" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for tuple")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                item_type: Some(Box::new(item_type)),
                ..default_type_descriptor(TypeKind::Tuple)
            })
        }
        "union" => {
            let variants_raw: Vec<Bound<'_, PyDict>> = raw.get_item("union_variants")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union")
            })?.extract()?;
            let variants: Vec<TypeDescriptor> = variants_raw
                .iter()
                .map(|v| build_type_descriptor_from_dict(v))
                .collect::<PyResult<_>>()?;

            Ok(TypeDescriptor {
                union_variants: Some(variants),
                ..default_type_descriptor(TypeKind::Union)
            })
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown type_kind: {type_kind}")
        )),
    }
}

fn parse_field_type(s: &str) -> PyResult<FieldType> {
    FieldType::from_str(s).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Unknown field type: {s}"))
    })
}

fn default_type_descriptor(type_kind: TypeKind) -> TypeDescriptor {
    TypeDescriptor {
        type_kind,
        primitive_type: None,
        primitive_serialize_fn: None,
        primitive_serialize_json_fn: None,
        primitive_serializer: None,
        primitive_deserializer: None,
        optional: false,
        inner_type: None,
        item_type: None,
        value_type: None,
        cls: None,
        fields: vec![],
        field_lookup: HashMap::new(),
        union_variants: None,
        can_use_direct_slots: false,
        has_post_init: false,
        serializer_fields: None,
        deserializer_fields: None,
    }
}

fn build_primitive_serializer(field_type: FieldType) -> Serializer {
    match field_type {
        FieldType::Str => Serializer::Str { strip_whitespaces: false },
        FieldType::Int => Serializer::Int,
        FieldType::Float => Serializer::Float,
        FieldType::Bool => Serializer::Bool,
        FieldType::Decimal => Serializer::Decimal(Box::new(SerDecimalData {
            decimal_places: DecimalPlaces::NotSpecified,
            decimal_rounding: None,
            invalid_error: None,
        })),
        FieldType::Date => Serializer::Date,
        FieldType::Time => Serializer::Time,
        FieldType::DateTime => Serializer::DateTime { format: None },
        FieldType::Uuid => Serializer::Uuid,
        _ => Serializer::Any,
    }
}

fn build_primitive_deserializer(field_type: FieldType) -> Deserializer {
    match field_type {
        FieldType::Str => Deserializer::Str { strip_whitespaces: false },
        FieldType::Int => Deserializer::Int,
        FieldType::Float => Deserializer::Float,
        FieldType::Bool => Deserializer::Bool,
        FieldType::Decimal => Deserializer::Decimal(Box::new(DecimalDeserData {
            decimal_places: DecimalPlaces::NotSpecified,
            decimal_rounding: None,
        })),
        FieldType::Date => Deserializer::Date,
        FieldType::Time => Deserializer::Time,
        FieldType::DateTime => Deserializer::DateTime { format: None },
        FieldType::Uuid => Deserializer::Uuid,
        _ => Deserializer::Any,
    }
}

fn extract_optional_py(raw: &Bound<'_, PyDict>, key: &str) -> PyResult<Option<Py<PyAny>>> {
    Ok(raw.get_item(key)?.filter(|v| !v.is_none()).map(pyo3::Bound::unbind))
}

fn extract_optional_dict<'py>(raw: &Bound<'py, PyDict>, key: &str) -> PyResult<Option<Bound<'py, PyDict>>> {
    match raw.get_item(key)?.filter(|v| !v.is_none()) {
        Some(v) => Ok(Some(v.cast_into()?)),
        None => Ok(None),
    }
}

fn extract_optional_dict_list<'py>(raw: &Bound<'py, PyDict>, key: &str) -> PyResult<Option<Vec<Bound<'py, PyDict>>>> {
    match raw.get_item(key)?.filter(|v| !v.is_none()) {
        Some(v) => Ok(Some(v.extract()?)),
        None => Ok(None),
    }
}

type EnumValues = (Option<Vec<(String, Py<PyAny>)>>, Option<Vec<(i64, Py<PyAny>)>>);

fn extract_enum_values(
    raw: &Bound<'_, PyDict>,
    field_type: FieldType,
) -> PyResult<EnumValues> {
    let enum_values_raw = match raw.get_item("enum_values")? {
        Some(v) if !v.is_none() => v,
        _ => return Ok((None, None)),
    };

    let enum_values_list: &Bound<'_, PyList> = enum_values_raw.cast()?;

    match field_type {
        FieldType::StrEnum => {
            let values = enum_values_list
                .iter()
                .map(|item| {
                    let tuple: &Bound<'_, PyTuple> = item.cast()?;
                    let key: String = tuple.get_item(0)?.extract()?;
                    let member: Py<PyAny> = tuple.get_item(1)?.extract()?;
                    Ok((key, member))
                })
                .collect::<PyResult<_>>()?;
            Ok((Some(values), None))
        }
        FieldType::IntEnum => {
            let values = enum_values_list
                .iter()
                .map(|item| {
                    let tuple: &Bound<'_, PyTuple> = item.cast()?;
                    let key: i64 = tuple.get_item(0)?.extract()?;
                    let member: Py<PyAny> = tuple.get_item(1)?.extract()?;
                    Ok((key, member))
                })
                .collect::<PyResult<_>>()?;
            Ok((None, Some(values)))
        }
        _ => Ok((None, None)),
    }
}

#[allow(clippy::too_many_lines)]
pub fn build_field_from_dict(raw: &Bound<'_, PyDict>) -> PyResult<FieldDescriptor> {
    let py = raw.py();
    let name: String = raw.get_item("name")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing name")
    })?.extract()?;
    let name_interned = PyString::intern(py, &name).unbind();

    let serialized_name: Option<String> = raw.get_item("serialized_name")?
        .and_then(|v| v.extract().ok());

    let field_type: String = raw.get_item("field_type")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing field_type")
    })?.extract()?;

    let optional: bool = raw.get_item("optional")?
        .is_some_and(|v| v.extract().unwrap_or(false));

    let slot_offset: Option<isize> = raw
        .get_item("slot_offset")?
        .and_then(|v| v.extract().ok())
        .filter(|&offset: &isize| offset.cast_unsigned().is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()));

    let strip_whitespaces: bool = raw.get_item("strip_whitespaces")?
        .is_some_and(|v| v.extract().unwrap_or(false));

    let decimal_places = match raw.get_item("decimal_places")? {
        None => DecimalPlaces::NotSpecified,
        Some(v) if v.is_none() => DecimalPlaces::NoRounding,
        Some(v) => DecimalPlaces::Places(v.extract().unwrap_or(2)),
    };

    let datetime_format: Option<String> = raw.get_item("datetime_format")?
        .and_then(|v| v.extract().ok());

    let nested_schema: Option<Box<SchemaDescriptor>> = extract_optional_dict(raw, "nested_schema")?
        .map(|d| build_schema_from_dict(&d).map(Box::new))
        .transpose()?;

    let item_schema: Option<Box<FieldDescriptor>> = extract_optional_dict(raw, "item_schema")?
        .map(|d| build_field_from_dict(&d).map(Box::new))
        .transpose()?;

    let value_schema: Option<Box<FieldDescriptor>> = extract_optional_dict(raw, "value_schema")?
        .map(|d| build_field_from_dict(&d).map(Box::new))
        .transpose()?;

    let enum_cls: Option<Py<PyAny>> = extract_optional_py(raw, "enum_cls")?;

    let parsed_field_type = parse_field_type(&field_type)?;
    let (str_enum_values, int_enum_values) = extract_enum_values(raw, parsed_field_type)?;

    let enum_name: Option<String> = raw.get_item("enum_name")?.and_then(|v| v.extract().ok());
    let enum_members_repr: Option<String> = raw.get_item("enum_members_repr")?.and_then(|v| v.extract().ok());

    let union_variants: Option<Vec<FieldDescriptor>> = extract_optional_dict_list(raw, "union_variants")?
        .map(|list| list.iter().map(|v| build_field_from_dict(v)).collect::<PyResult<_>>())
        .transpose()?;

    let default_value: Option<Py<PyAny>> = extract_optional_py(raw, "default_value")?;
    let default_factory: Option<Py<PyAny>> = extract_optional_py(raw, "default_factory")?;
    let decimal_rounding: Option<Py<PyAny>> = extract_optional_py(raw, "decimal_rounding")?;

    let required_error: Option<String> = raw.get_item("required_error")?.and_then(|v| v.extract().ok());
    let none_error: Option<String> = raw.get_item("none_error")?.and_then(|v| v.extract().ok());
    let invalid_error: Option<String> = raw.get_item("invalid_error")?.and_then(|v| v.extract().ok());
    let field_init: bool = raw.get_item("field_init")?.and_then(|v| v.extract().ok()).unwrap_or(true);

    let validator: Option<Py<PyAny>> = extract_optional_py(raw, "validator")?;
    let item_validator: Option<Py<PyAny>> = extract_optional_py(raw, "item_validator")?;
    let value_validator: Option<Py<PyAny>> = extract_optional_py(raw, "value_validator")?;

    Ok(FieldDescriptor {
        name,
        name_interned,
        serialized_name,
        field_type: parsed_field_type,
        serialize_fn: callback_required_serialize,
        serialize_json_fn: callback_required_serialize_json,
        deserialize_fn: callback_required_deserialize,
        optional,
        slot_offset,
        nested_schema,
        item_schema,
        value_schema,
        strip_whitespaces,
        decimal_places,
        decimal_rounding,
        datetime_format,
        enum_cls,
        str_enum_values,
        int_enum_values,
        enum_name,
        enum_members_repr,
        union_variants,
        default_value,
        default_factory,
        required_error,
        none_error,
        invalid_error,
        field_init,
        validator,
        item_validator,
        value_validator,
    })
}

pub fn build_schema_from_dict(raw: &Bound<'_, PyDict>) -> PyResult<SchemaDescriptor> {
    let cls: Py<PyAny> = raw.get_item("cls")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing cls")
    })?.extract()?;

    let fields_raw: Vec<Bound<'_, PyDict>> = raw.get_item("fields")?.ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing fields")
    })?.extract()?;

    let fields: Vec<FieldDescriptor> = fields_raw
        .iter()
        .map(|f| build_field_from_dict(f))
        .collect::<PyResult<_>>()?;

    let can_use_direct_slots: bool = raw.get_item("can_use_direct_slots")?
        .is_some_and(|v| v.extract().unwrap_or(false));

    let has_post_init: bool = raw.get_item("has_post_init")?
        .is_some_and(|v| v.extract().unwrap_or(false));

    let py = raw.py();
    let field_lookup = build_field_lookup(&fields);
    let serializer_fields = build_serializer_fields(py, &fields);
    let deserializer_fields = build_deserializer_fields(py, &fields);
    Ok(SchemaDescriptor { cls, fields, field_lookup, can_use_direct_slots, has_post_init, serializer_fields: Some(serializer_fields), deserializer_fields: Some(deserializer_fields) })
}

fn clone_py_opt(py: Python<'_>, opt: Option<&Py<PyAny>>) -> Option<Py<PyAny>> {
    opt.map(|v| v.clone_ref(py))
}

fn build_serializer_from_field(py: Python<'_>, field: &FieldDescriptor) -> Serializer {
    match field.field_type {
        FieldType::Str => Serializer::Str { strip_whitespaces: field.strip_whitespaces },
        FieldType::Int => Serializer::Int,
        FieldType::Float => Serializer::Float,
        FieldType::Bool => Serializer::Bool,
        FieldType::Decimal => Serializer::Decimal(Box::new(SerDecimalData {
            decimal_places: field.decimal_places,
            decimal_rounding: clone_py_opt(py, field.decimal_rounding.as_ref()),
            invalid_error: field.invalid_error.clone(),
        })),
        FieldType::Date => Serializer::Date,
        FieldType::Time => Serializer::Time,
        FieldType::DateTime => Serializer::DateTime { format: field.datetime_format.clone() },
        FieldType::Uuid => Serializer::Uuid,
        FieldType::StrEnum => Serializer::StrEnum(Box::new(StrEnumData {
            enum_cls: field.enum_cls.as_ref().expect("enum_cls required for StrEnum").clone_ref(py),
            enum_name: field.enum_name.clone(),
            enum_members_repr: field.enum_members_repr.clone(),
        })),
        FieldType::IntEnum => Serializer::IntEnum(Box::new(IntEnumData {
            enum_cls: field.enum_cls.as_ref().expect("enum_cls required for IntEnum").clone_ref(py),
            enum_name: field.enum_name.clone(),
            enum_members_repr: field.enum_members_repr.clone(),
        })),
        FieldType::Any => Serializer::Any,
        FieldType::List => Serializer::Collection(Box::new(CollectionData {
            item: Box::new(build_serializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for List"))),
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
            kind: CollectionKind::List,
        })),
        FieldType::Set => Serializer::Collection(Box::new(CollectionData {
            item: Box::new(build_serializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for Set"))),
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
            kind: CollectionKind::Set,
        })),
        FieldType::FrozenSet => Serializer::Collection(Box::new(CollectionData {
            item: Box::new(build_serializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for FrozenSet"))),
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
            kind: CollectionKind::FrozenSet,
        })),
        FieldType::Tuple => Serializer::Collection(Box::new(CollectionData {
            item: Box::new(build_serializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for Tuple"))),
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
            kind: CollectionKind::Tuple,
        })),
        FieldType::Dict => Serializer::Dict(Box::new(DictData {
            value: Box::new(build_serializer_from_field(py, field.value_schema.as_ref().expect("value_schema required for Dict"))),
            value_validator: clone_py_opt(py, field.value_validator.as_ref()),
        })),
        FieldType::Nested => {
            let nested = field.nested_schema.as_ref().expect("nested_schema required for Nested");
            Serializer::Nested {
                schema: Box::new(build_dataclass_serializer_schema(py, nested))
            }
        }
        FieldType::Union => {
            let variants = field.union_variants.as_ref().expect("union_variants required for Union");
            Serializer::Union {
                variants: variants.iter().map(|v| build_serializer_from_field(py, v)).collect()
            }
        }
    }
}

fn build_dataclass_serializer_schema(py: Python<'_>, schema: &SchemaDescriptor) -> DataclassSerializerSchema {
    let fields: Vec<FieldSerializer> = schema.fields.iter().map(|f| build_field_serializer(py, f)).collect();
    let field_lookup = fields.iter().enumerate()
        .map(|(idx, f)| (f.serialized_name.as_ref().unwrap_or(&f.name).clone(), idx))
        .collect();
    DataclassSerializerSchema {
        cls: schema.cls.clone_ref(py),
        fields,
        field_lookup,
        can_use_direct_slots: schema.can_use_direct_slots,
        has_post_init: schema.has_post_init,
    }
}

fn build_field_serializer(py: Python<'_>, field: &FieldDescriptor) -> FieldSerializer {
    FieldSerializer {
        name: field.name.clone(),
        name_interned: field.name_interned.clone_ref(py),
        serialized_name: field.serialized_name.clone(),
        serializer: build_serializer_from_field(py, field),
        optional: field.optional,
        slot_offset: field.slot_offset,
        validator: clone_py_opt(py, field.validator.as_ref()),
    }
}

fn clone_py_vec<T: Clone>(py: Python<'_>, values: &[(T, Py<PyAny>)]) -> Vec<(T, Py<PyAny>)> {
    values.iter().map(|(k, v)| (k.clone(), v.clone_ref(py))).collect()
}

fn build_deserializer_from_field(py: Python<'_>, field: &FieldDescriptor) -> Deserializer {
    match field.field_type {
        FieldType::Str => Deserializer::Str { strip_whitespaces: field.strip_whitespaces },
        FieldType::Int => Deserializer::Int,
        FieldType::Float => Deserializer::Float,
        FieldType::Bool => Deserializer::Bool,
        FieldType::Decimal => Deserializer::Decimal(Box::new(DecimalDeserData {
            decimal_places: field.decimal_places,
            decimal_rounding: clone_py_opt(py, field.decimal_rounding.as_ref()),
        })),
        FieldType::Date => Deserializer::Date,
        FieldType::Time => Deserializer::Time,
        FieldType::DateTime => Deserializer::DateTime { format: field.datetime_format.clone() },
        FieldType::Uuid => Deserializer::Uuid,
        FieldType::StrEnum => Deserializer::StrEnum(Box::new(StrEnumDeserData {
            values: clone_py_vec(py, field.str_enum_values.as_ref().expect("str_enum_values required for StrEnum")),
        })),
        FieldType::IntEnum => Deserializer::IntEnum(Box::new(IntEnumDeserData {
            values: clone_py_vec(py, field.int_enum_values.as_ref().expect("int_enum_values required for IntEnum")),
        })),
        FieldType::Any => Deserializer::Any,
        FieldType::List => Deserializer::Collection(Box::new(CollectionDeserData {
            item: Box::new(build_deserializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for List"))),
            kind: CollectionKind::List,
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
        })),
        FieldType::Set => Deserializer::Collection(Box::new(CollectionDeserData {
            item: Box::new(build_deserializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for Set"))),
            kind: CollectionKind::Set,
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
        })),
        FieldType::FrozenSet => Deserializer::Collection(Box::new(CollectionDeserData {
            item: Box::new(build_deserializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for FrozenSet"))),
            kind: CollectionKind::FrozenSet,
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
        })),
        FieldType::Tuple => Deserializer::Collection(Box::new(CollectionDeserData {
            item: Box::new(build_deserializer_from_field(py, field.item_schema.as_ref().expect("item_schema required for Tuple"))),
            kind: CollectionKind::Tuple,
            item_validator: clone_py_opt(py, field.item_validator.as_ref()),
        })),
        FieldType::Dict => Deserializer::Dict(Box::new(DictDeserData {
            value: Box::new(build_deserializer_from_field(py, field.value_schema.as_ref().expect("value_schema required for Dict"))),
            value_validator: clone_py_opt(py, field.value_validator.as_ref()),
        })),
        FieldType::Nested => {
            let nested = field.nested_schema.as_ref().expect("nested_schema required for Nested");
            Deserializer::Nested {
                schema: Box::new(build_dataclass_deserializer_schema(py, nested))
            }
        }
        FieldType::Union => {
            let variants = field.union_variants.as_ref().expect("union_variants required for Union");
            Deserializer::Union {
                variants: variants.iter().map(|v| build_deserializer_from_field(py, v)).collect()
            }
        }
    }
}

fn build_dataclass_deserializer_schema(py: Python<'_>, schema: &SchemaDescriptor) -> DataclassDeserializerSchema {
    let fields: Vec<FieldDeserializer> = schema.fields.iter().map(|f| build_field_deserializer(py, f)).collect();
    let field_lookup = fields.iter().enumerate()
        .map(|(idx, f)| (f.serialized_name.as_ref().unwrap_or(&f.name).clone(), idx))
        .collect();
    DataclassDeserializerSchema {
        cls: schema.cls.clone_ref(py),
        fields,
        field_lookup,
        can_use_direct_slots: schema.can_use_direct_slots,
        has_post_init: schema.has_post_init,
    }
}

fn build_field_deserializer(py: Python<'_>, field: &FieldDescriptor) -> FieldDeserializer {
    FieldDeserializer {
        name: field.name.clone(),
        name_interned: field.name_interned.clone_ref(py),
        serialized_name: field.serialized_name.clone(),
        deserializer: build_deserializer_from_field(py, field),
        optional: field.optional,
        slot_offset: field.slot_offset,
        default_value: clone_py_opt(py, field.default_value.as_ref()),
        default_factory: clone_py_opt(py, field.default_factory.as_ref()),
        required_error: field.required_error.clone(),
        none_error: field.none_error.clone(),
        invalid_error: field.invalid_error.clone(),
        field_init: field.field_init,
        validator: clone_py_opt(py, field.validator.as_ref()),
        item_validator: clone_py_opt(py, field.item_validator.as_ref()),
        value_validator: clone_py_opt(py, field.value_validator.as_ref()),
    }
}

pub fn build_serializer_fields(py: Python<'_>, fields: &[FieldDescriptor]) -> Vec<FieldSerializer> {
    fields.iter().map(|f| build_field_serializer(py, f)).collect()
}

pub fn build_deserializer_fields(py: Python<'_>, fields: &[FieldDescriptor]) -> Vec<FieldDeserializer> {
    fields.iter().map(|f| build_field_deserializer(py, f)).collect()
}
