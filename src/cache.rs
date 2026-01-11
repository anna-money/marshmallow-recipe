use once_cell::sync::{Lazy, OnceCell};
use pyo3::ffi;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString, PyTuple};
use pyo3::BoundObject;
use std::collections::HashMap;
use std::sync::RwLock;

use crate::types::{FieldDescriptor, FieldType, SchemaDescriptor, TypeDescriptor, TypeKind};

fn force_setattr<'py, N, V>(py: Python<'py>, obj: &Bound<'py, PyAny>, attr_name: N, value: V) -> PyResult<()>
where
    N: IntoPyObject<'py>,
    V: IntoPyObject<'py>,
{
    let attr_name = attr_name.into_pyobject(py).map_err(Into::into)?;
    let value = value.into_pyobject(py).map_err(Into::into)?;
    let result = unsafe {
        ffi::PyObject_GenericSetAttr(obj.as_ptr(), attr_name.as_ptr(), value.as_ptr())
    };
    if result == -1 {
        Err(PyErr::fetch(py))
    } else {
        Ok(())
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

pub static SCHEMA_CACHE: Lazy<RwLock<HashMap<u64, TypeDescriptor>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));

pub struct CachedPyTypes {
    pub int_cls: Py<PyAny>,
    pub decimal_cls: Py<PyAny>,
    pub uuid_cls: Py<PyAny>,
    pub safe_uuid_unknown: Py<PyAny>,
    pub datetime_cls: Py<PyAny>,
    pub date_cls: Py<PyAny>,
    pub time_cls: Py<PyAny>,
    pub utc_tz: Py<PyAny>,
    pub object_cls: Py<PyAny>,
    pub quantize_0: Py<PyAny>,
    pub quantize_1: Py<PyAny>,
    pub quantize_2: Py<PyAny>,
    pub quantize_3: Py<PyAny>,
    pub quantize_4: Py<PyAny>,
    pub quantize_5: Py<PyAny>,
    pub quantize_6: Py<PyAny>,
    pub quantize_8: Py<PyAny>,
    pub quantize_12: Py<PyAny>,
    pub str_fromisoformat: Py<PyString>,
    pub str_strptime: Py<PyString>,
    pub str_new: Py<PyString>,
    pub str_quantize: Py<PyString>,
    pub str_replace: Py<PyString>,
    pub str_strftime: Py<PyString>,
    pub str_isoformat: Py<PyString>,
    pub str_tzinfo: Py<PyString>,
    pub str_rounding: Py<PyString>,
    pub str_value: Py<PyString>,
    pub str_int: Py<PyString>,
    pub str_is_safe: Py<PyString>,
    pub str_utcoffset: Py<PyString>,
    pub missing_sentinel: Py<PyAny>,
}

impl CachedPyTypes {
    pub const fn get_quantizer(&self, places: i32) -> Option<&Py<PyAny>> {
        match places {
            0 => Some(&self.quantize_0),
            1 => Some(&self.quantize_1),
            2 => Some(&self.quantize_2),
            3 => Some(&self.quantize_3),
            4 => Some(&self.quantize_4),
            5 => Some(&self.quantize_5),
            6 => Some(&self.quantize_6),
            8 => Some(&self.quantize_8),
            12 => Some(&self.quantize_12),
            _ => None,
        }
    }

    pub fn create_uuid_fast(&self, py: Python, uuid_int: u128) -> PyResult<Py<PyAny>> {
        let uuid_cls = self.uuid_cls.bind(py);
        let uuid_obj = uuid_cls.call_method1(self.str_new.bind(py), (&uuid_cls,))?;
        force_setattr(py, &uuid_obj, self.str_int.bind(py), uuid_int)?;
        force_setattr(py, &uuid_obj, self.str_is_safe.bind(py), &self.safe_uuid_unknown)?;
        Ok(uuid_obj.unbind())
    }
}

static CACHED_PY_TYPES: OnceCell<CachedPyTypes> = OnceCell::new();

pub fn get_cached_types(py: Python) -> PyResult<&'static CachedPyTypes> {
    CACHED_PY_TYPES.get_or_try_init(|| {
        let decimal_mod = py.import("decimal")?;
        let uuid_mod = py.import("uuid")?;
        let datetime_mod = py.import("datetime")?;
        let builtins = py.import("builtins")?;
        let mr_missing_mod = py.import("marshmallow_recipe.missing")?;

        let decimal_cls = decimal_mod.getattr("Decimal")?;

        Ok(CachedPyTypes {
            int_cls: builtins.getattr("int")?.unbind(),
            quantize_0: decimal_cls.call1(("1e-0",))?.unbind(),
            quantize_1: decimal_cls.call1(("1e-1",))?.unbind(),
            quantize_2: decimal_cls.call1(("1e-2",))?.unbind(),
            quantize_3: decimal_cls.call1(("1e-3",))?.unbind(),
            quantize_4: decimal_cls.call1(("1e-4",))?.unbind(),
            quantize_5: decimal_cls.call1(("1e-5",))?.unbind(),
            quantize_6: decimal_cls.call1(("1e-6",))?.unbind(),
            quantize_8: decimal_cls.call1(("1e-8",))?.unbind(),
            quantize_12: decimal_cls.call1(("1e-12",))?.unbind(),
            decimal_cls: decimal_cls.unbind(),
            uuid_cls: uuid_mod.getattr("UUID")?.unbind(),
            safe_uuid_unknown: uuid_mod.getattr("SafeUUID")?.getattr("unknown")?.unbind(),
            datetime_cls: datetime_mod.getattr("datetime")?.unbind(),
            date_cls: datetime_mod.getattr("date")?.unbind(),
            time_cls: datetime_mod.getattr("time")?.unbind(),
            utc_tz: datetime_mod.getattr("UTC")?.unbind(),
            object_cls: builtins.getattr("object")?.unbind(),
            str_fromisoformat: PyString::intern(py, "fromisoformat").unbind(),
            str_strptime: PyString::intern(py, "strptime").unbind(),
            str_new: PyString::intern(py, "__new__").unbind(),
            str_quantize: PyString::intern(py, "quantize").unbind(),
            str_replace: PyString::intern(py, "replace").unbind(),
            str_strftime: PyString::intern(py, "strftime").unbind(),
            str_isoformat: PyString::intern(py, "isoformat").unbind(),
            str_tzinfo: PyString::intern(py, "tzinfo").unbind(),
            str_rounding: PyString::intern(py, "rounding").unbind(),
            str_value: PyString::intern(py, "value").unbind(),
            str_int: PyString::intern(py, "int").unbind(),
            str_is_safe: PyString::intern(py, "is_safe").unbind(),
            str_utcoffset: PyString::intern(py, "utcoffset").unbind(),
            missing_sentinel: mr_missing_mod.getattr("MISSING")?.unbind(),
        })
    })
}

#[pyfunction]
#[pyo3(signature = (schema_id, raw_schema))]
pub fn register(_py: Python, schema_id: u64, raw_schema: &Bound<'_, PyDict>) -> PyResult<()> {
    let descriptor = build_type_descriptor_from_dict(raw_schema)?;
    let mut cache = SCHEMA_CACHE.write().unwrap_or_else(std::sync::PoisonError::into_inner);
    cache.insert(schema_id, descriptor);
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

            let field_lookup = build_field_lookup(&fields);
            Ok(TypeDescriptor {
                type_kind: TypeKind::Dataclass,
                primitive_type: None,
                optional: false,
                inner_type: None,
                item_type: None,
                key_type: None,
                value_type: None,
                cls: Some(cls),
                fields,
                field_lookup,
                union_variants: None,
                can_use_direct_slots,
                has_post_init,
            })
        }
        "primitive" => {
            let primitive_type: String = raw.get_item("primitive_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_type")
            })?.extract()?;

            Ok(TypeDescriptor {
                type_kind: TypeKind::Primitive,
                primitive_type: Some(parse_field_type(&primitive_type)?),
                optional: false,
                inner_type: None,
                item_type: None,
                key_type: None,
                value_type: None,
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        "list" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                type_kind: TypeKind::List,
                primitive_type: None,
                optional: false,
                inner_type: None,
                item_type: Some(Box::new(item_type)),
                key_type: None,
                value_type: None,
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        "dict" => {
            let key_type: String = raw.get_item("key_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing key_type")
            })?.extract()?;
            let value_raw: Bound<'_, PyDict> = raw.get_item("value_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type")
            })?.extract()?;
            let value_type = build_type_descriptor_from_dict(&value_raw)?;

            Ok(TypeDescriptor {
                type_kind: TypeKind::Dict,
                primitive_type: None,
                optional: false,
                inner_type: None,
                item_type: None,
                key_type: Some(parse_field_type(&key_type)?),
                value_type: Some(Box::new(value_type)),
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        "optional" => {
            let inner_raw: Bound<'_, PyDict> = raw.get_item("inner_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type")
            })?.extract()?;
            let inner_type = build_type_descriptor_from_dict(&inner_raw)?;

            Ok(TypeDescriptor {
                type_kind: TypeKind::Optional,
                primitive_type: None,
                optional: true,
                inner_type: Some(Box::new(inner_type)),
                item_type: None,
                key_type: None,
                value_type: None,
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        "set" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for set")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                type_kind: TypeKind::Set,
                primitive_type: None,
                optional: false,
                inner_type: None,
                item_type: Some(Box::new(item_type)),
                key_type: None,
                value_type: None,
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        "frozenset" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for frozenset")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                type_kind: TypeKind::FrozenSet,
                primitive_type: None,
                optional: false,
                inner_type: None,
                item_type: Some(Box::new(item_type)),
                key_type: None,
                value_type: None,
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        "tuple" => {
            let item_raw: Bound<'_, PyDict> = raw.get_item("item_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for tuple")
            })?.extract()?;
            let item_type = build_type_descriptor_from_dict(&item_raw)?;

            Ok(TypeDescriptor {
                type_kind: TypeKind::Tuple,
                primitive_type: None,
                optional: false,
                inner_type: None,
                item_type: Some(Box::new(item_type)),
                key_type: None,
                value_type: None,
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
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
                type_kind: TypeKind::Union,
                primitive_type: None,
                optional: false,
                inner_type: None,
                item_type: None,
                key_type: None,
                value_type: None,
                cls: None,
                fields: vec![],
                field_lookup: HashMap::new(),
                union_variants: Some(variants),
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown type_kind: {type_kind}")
        )),
    }
}

pub fn parse_field_type(s: &str) -> PyResult<FieldType> {
    match s {
        "str" => Ok(FieldType::Str),
        "int" => Ok(FieldType::Int),
        "float" => Ok(FieldType::Float),
        "bool" => Ok(FieldType::Bool),
        "decimal" => Ok(FieldType::Decimal),
        "uuid" => Ok(FieldType::Uuid),
        "datetime" => Ok(FieldType::DateTime),
        "date" => Ok(FieldType::Date),
        "time" => Ok(FieldType::Time),
        "list" => Ok(FieldType::List),
        "dict" => Ok(FieldType::Dict),
        "nested" => Ok(FieldType::Nested),
        "str_enum" => Ok(FieldType::StrEnum),
        "int_enum" => Ok(FieldType::IntEnum),
        "set" => Ok(FieldType::Set),
        "frozenset" => Ok(FieldType::FrozenSet),
        "tuple" => Ok(FieldType::Tuple),
        "union" => Ok(FieldType::Union),
        "any" => Ok(FieldType::Any),
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown field type: {s}")
        )),
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

    // slot_offset is used for direct memory access to Python object slots.
    // We only use it if the offset is properly aligned for pointer access.
    // Unaligned offsets can occur if a dataclass inherits from a C extension
    // with a misaligned tp_basicsize (see CPython issue #129675).
    // If unaligned, we fall back to regular getattr access.
    let slot_offset: Option<isize> = raw.get_item("slot_offset")?
        .and_then(|v| v.extract().ok())
        .filter(|&offset: &isize| offset.cast_unsigned().is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()));

    let strip_whitespaces: bool = raw.get_item("strip_whitespaces")?
        .is_some_and(|v| v.extract().unwrap_or(false));

    let decimal_places: Option<i32> = raw.get_item("decimal_places")?
        .and_then(|v| v.extract().ok());

    let decimal_as_string: bool = raw.get_item("decimal_as_string")?
        .is_none_or(|v| v.extract().unwrap_or(true));

    let datetime_format: Option<String> = raw.get_item("datetime_format")?
        .and_then(|v| v.extract().ok());

    let nested_schema: Option<Box<SchemaDescriptor>> = if let Some(nested_raw) = raw.get_item("nested_schema")? {
        if nested_raw.is_none() {
            None
        } else {
            let nested_dict: Bound<'_, PyDict> = nested_raw.extract()?;
            Some(Box::new(build_schema_from_dict(&nested_dict)?))
        }
    } else {
        None
    };

    let item_schema: Option<Box<FieldDescriptor>> = if let Some(item_raw) = raw.get_item("item_schema")? {
        if item_raw.is_none() {
            None
        } else {
            let item_dict: Bound<'_, PyDict> = item_raw.extract()?;
            Some(Box::new(build_field_from_dict(&item_dict)?))
        }
    } else {
        None
    };

    let key_type: Option<FieldType> = if let Some(kt) = raw.get_item("key_type")? {
        if kt.is_none() {
            None
        } else {
            let kt_str: String = kt.extract()?;
            Some(parse_field_type(&kt_str)?)
        }
    } else {
        None
    };

    let value_schema: Option<Box<FieldDescriptor>> = if let Some(value_raw) = raw.get_item("value_schema")? {
        if value_raw.is_none() {
            None
        } else {
            let value_dict: Bound<'_, PyDict> = value_raw.extract()?;
            Some(Box::new(build_field_from_dict(&value_dict)?))
        }
    } else {
        None
    };

    let enum_cls: Option<Py<PyAny>> = if let Some(cls_raw) = raw.get_item("enum_cls")? {
        if cls_raw.is_none() {
            None
        } else {
            Some(cls_raw.extract()?)
        }
    } else {
        None
    };

    let mut str_enum_values: Option<Vec<(String, Py<PyAny>)>> = None;
    let mut int_enum_values: Option<Vec<(i64, Py<PyAny>)>> = None;

    if let Some(enum_values_raw) = raw.get_item("enum_values")? {
        if !enum_values_raw.is_none() {
            let enum_values_list: &Bound<'_, PyList> = enum_values_raw.cast()?;
            let field_type_str: String = raw.get_item("field_type")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing field_type")
            })?.extract()?;

            if field_type_str == "str_enum" {
                let mut values = Vec::with_capacity(enum_values_list.len());
                for item in enum_values_list.iter() {
                    let tuple: &Bound<'_, PyTuple> = item.cast()?;
                    let key: String = tuple.get_item(0)?.extract()?;
                    let member: Py<PyAny> = tuple.get_item(1)?.extract()?;
                    values.push((key, member));
                }
                str_enum_values = Some(values);
            } else if field_type_str == "int_enum" {
                let mut values = Vec::with_capacity(enum_values_list.len());
                for item in enum_values_list.iter() {
                    let tuple: &Bound<'_, PyTuple> = item.cast()?;
                    let key: i64 = tuple.get_item(0)?.extract()?;
                    let member: Py<PyAny> = tuple.get_item(1)?.extract()?;
                    values.push((key, member));
                }
                int_enum_values = Some(values);
            }
        }
    }

    let enum_name: Option<String> = raw.get_item("enum_name")?.and_then(|v| v.extract().ok());
    let enum_members_repr: Option<String> = raw.get_item("enum_members_repr")?.and_then(|v| v.extract().ok());

    let union_variants: Option<Vec<FieldDescriptor>> = if let Some(variants_raw) = raw.get_item("union_variants")? {
        if variants_raw.is_none() {
            None
        } else {
            let variants_list: Vec<Bound<'_, PyDict>> = variants_raw.extract()?;
            let variants: Vec<FieldDescriptor> = variants_list
                .iter()
                .map(|v| build_field_from_dict(v))
                .collect::<PyResult<_>>()?;
            Some(variants)
        }
    } else {
        None
    };

    let default_value: Option<Py<PyAny>> = if let Some(dv) = raw.get_item("default_value")? {
        if dv.is_none() {
            None
        } else {
            Some(dv.extract()?)
        }
    } else {
        None
    };

    let default_factory: Option<Py<PyAny>> = if let Some(df) = raw.get_item("default_factory")? {
        if df.is_none() {
            None
        } else {
            Some(df.extract()?)
        }
    } else {
        None
    };

    let decimal_rounding: Option<Py<PyAny>> = if let Some(dr) = raw.get_item("decimal_rounding")? {
        if dr.is_none() {
            None
        } else {
            Some(dr.extract()?)
        }
    } else {
        None
    };

    let required_error: Option<String> = raw.get_item("required_error")?.and_then(|v| v.extract().ok());
    let none_error: Option<String> = raw.get_item("none_error")?.and_then(|v| v.extract().ok());
    let invalid_error: Option<String> = raw.get_item("invalid_error")?.and_then(|v| v.extract().ok());
    let field_init: bool = raw.get_item("field_init")?.and_then(|v| v.extract().ok()).unwrap_or(true);

    let validator: Option<Py<PyAny>> = if let Some(v) = raw.get_item("validator")? {
        if v.is_none() {
            None
        } else {
            Some(v.extract()?)
        }
    } else {
        None
    };

    let item_validator: Option<Py<PyAny>> = if let Some(v) = raw.get_item("item_validator")? {
        if v.is_none() {
            None
        } else {
            Some(v.extract()?)
        }
    } else {
        None
    };

    let value_validator: Option<Py<PyAny>> = if let Some(v) = raw.get_item("value_validator")? {
        if v.is_none() {
            None
        } else {
            Some(v.extract()?)
        }
    } else {
        None
    };

    Ok(FieldDescriptor {
        name,
        name_interned,
        serialized_name,
        field_type: parse_field_type(&field_type)?,
        optional,
        slot_offset,
        nested_schema,
        item_schema,
        key_type,
        value_schema,
        strip_whitespaces,
        decimal_places,
        decimal_as_string,
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

    let field_lookup = build_field_lookup(&fields);
    Ok(SchemaDescriptor { cls, fields, field_lookup, can_use_direct_slots, has_post_init })
}
