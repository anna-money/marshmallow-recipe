use pyo3::prelude::*;
use pyo3::conversion::IntoPyObjectExt;
use pyo3::types::{PyBytes, PyDict, PyList, PyString};
use serde_json::{Map, Value};
use std::borrow::Cow;
use std::collections::HashMap;
use std::sync::RwLock;
use once_cell::sync::{Lazy, OnceCell};
use encoding_rs::Encoding;

static SCHEMA_CACHE: Lazy<RwLock<HashMap<u64, TypeDescriptor>>> =
    Lazy::new(|| RwLock::new(HashMap::new()));

struct CachedPyTypes {
    decimal_cls: Py<PyAny>,
    uuid_cls: Py<PyAny>,
    datetime_cls: Py<PyAny>,
    date_cls: Py<PyAny>,
    time_cls: Py<PyAny>,
    utc_tz: Py<PyAny>,
    set_cls: Py<PyAny>,
    frozenset_cls: Py<PyAny>,
    tuple_cls: Py<PyAny>,
    object_cls: Py<PyAny>,
}

static CACHED_PY_TYPES: OnceCell<CachedPyTypes> = OnceCell::new();

fn get_cached_types(py: Python) -> PyResult<&'static CachedPyTypes> {
    CACHED_PY_TYPES.get_or_try_init(|| {
        let decimal_mod = py.import("decimal")?;
        let uuid_mod = py.import("uuid")?;
        let datetime_mod = py.import("datetime")?;
        let builtins = py.import("builtins")?;

        Ok(CachedPyTypes {
            decimal_cls: decimal_mod.getattr("Decimal")?.unbind(),
            uuid_cls: uuid_mod.getattr("UUID")?.unbind(),
            datetime_cls: datetime_mod.getattr("datetime")?.unbind(),
            date_cls: datetime_mod.getattr("date")?.unbind(),
            time_cls: datetime_mod.getattr("time")?.unbind(),
            utc_tz: datetime_mod.getattr("UTC")?.unbind(),
            set_cls: builtins.getattr("set")?.unbind(),
            frozenset_cls: builtins.getattr("frozenset")?.unbind(),
            tuple_cls: builtins.getattr("tuple")?.unbind(),
            object_cls: builtins.getattr("object")?.unbind(),
        })
    })
}

fn normalize_encoding_label(encoding: &str) -> &str {
    if encoding.eq_ignore_ascii_case("latin-1")
        || encoding.eq_ignore_ascii_case("latin1")
        || encoding.eq_ignore_ascii_case("iso-8859-1")
        || encoding.eq_ignore_ascii_case("iso8859-1")
    {
        return "windows-1252";
    }
    encoding
}

fn create_field_validation_error_with_custom(py: Python, field_name: &str, default_message: &str, custom_message: Option<&str>) -> PyErr {
    let error_dict = PyDict::new(py);
    let message = custom_message.unwrap_or(default_message);
    let msg_list = PyList::new(py, vec![message]).unwrap();
    error_dict.set_item(field_name, msg_list).unwrap();
    let builtins = py.import("builtins").unwrap();
    let value_error = builtins.getattr("ValueError").unwrap();
    let error_instance = value_error.call1((error_dict,)).unwrap();
    PyErr::from_value(error_instance.into_any())
}

fn create_field_validation_error(py: Python, field_name: &str, message: &str) -> PyErr {
    create_field_validation_error_with_custom(py, field_name, message, None)
}

fn create_validation_error(py: Python, field_name: &str, message: &str) -> PyErr {
    let marshmallow = py.import("marshmallow").unwrap();
    let validation_error_cls = marshmallow.getattr("ValidationError").unwrap();
    let error_dict = PyDict::new(py);
    let msg_list = PyList::new(py, vec![message]).unwrap();
    error_dict.set_item(field_name, msg_list).unwrap();
    let error_instance = validation_error_cls.call1((error_dict,)).unwrap();
    PyErr::from_value(error_instance.into_any())
}

fn decode_to_utf8_bytes<'a>(bytes: &'a [u8], encoding: &str) -> PyResult<Cow<'a, [u8]>> {
    if encoding.eq_ignore_ascii_case("utf-8") || encoding.eq_ignore_ascii_case("utf8") {
        return Ok(Cow::Borrowed(bytes));
    }
    if encoding.eq_ignore_ascii_case("ascii") {
        if bytes.iter().any(|&b| b > 127) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "ASCII decoding error: byte > 127"
            ));
        }
        return Ok(Cow::Borrowed(bytes));
    }
    let label = normalize_encoding_label(encoding);
    let enc = Encoding::for_label(label.as_bytes())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown encoding: {}", encoding)
        ))?;
    let mut decoder = enc.new_decoder();
    let max_len = decoder.max_utf8_buffer_length(bytes.len())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Buffer size overflow"))?;
    let mut output = vec![0u8; max_len];
    let (result, _, written, _) = decoder.decode_to_utf8(bytes, &mut output, true);
    if result == encoding_rs::CoderResult::InputEmpty {
        output.truncate(written);
        Ok(Cow::Owned(output))
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to decode with encoding: {}", enc.name())
        ))
    }
}

fn encode_from_utf8_bytes<'a>(utf8_bytes: &'a [u8], encoding: &str) -> PyResult<Cow<'a, [u8]>> {
    if encoding.eq_ignore_ascii_case("utf-8") || encoding.eq_ignore_ascii_case("utf8") {
        return Ok(Cow::Borrowed(utf8_bytes));
    }
    if encoding.eq_ignore_ascii_case("ascii") {
        if utf8_bytes.iter().any(|&b| b > 127) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "ASCII encoding error: non-ASCII character in output"
            ));
        }
        return Ok(Cow::Borrowed(utf8_bytes));
    }
    let label = normalize_encoding_label(encoding);
    let enc = Encoding::for_label(label.as_bytes())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown encoding: {}", encoding)
        ))?;
    let utf8_str = std::str::from_utf8(utf8_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let mut encoder = enc.new_encoder();
    let max_len = encoder.max_buffer_length_from_utf8_if_no_unmappables(utf8_str.len())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Buffer size overflow"))?;
    let mut output = vec![0u8; max_len];
    let (result, _, written, _) = encoder.encode_from_utf8(utf8_str, &mut output, true);
    if result == encoding_rs::CoderResult::InputEmpty {
        output.truncate(written);
        Ok(Cow::Owned(output))
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to encode with encoding: {}", enc.name())
        ))
    }
}

#[derive(Clone, Debug, PartialEq)]
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
}

impl<'py> FromPyObject<'py> for FieldType {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let s: String = ob.extract()?;
        match s.as_str() {
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
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Unknown field type: {}", s),
            )),
        }
    }
}

#[derive(Debug)]
pub struct FieldDescriptor {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub serialized_name: Option<String>,
    pub field_type: FieldType,
    pub optional: bool,
    pub slot_offset: Option<isize>,
    pub nested_schema: Option<Box<SchemaDescriptor>>,
    pub item_schema: Option<Box<FieldDescriptor>>,
    pub key_type: Option<FieldType>,
    pub value_schema: Option<Box<FieldDescriptor>>,
    pub strip_whitespaces: bool,
    pub decimal_places: Option<i32>,
    pub decimal_as_string: bool,
    pub decimal_rounding: Option<Py<PyAny>>,
    pub datetime_format: Option<String>,
    pub enum_cls: Option<Py<PyAny>>,
    pub union_variants: Option<Vec<Box<FieldDescriptor>>>,
    pub default_value: Option<Py<PyAny>>,
    pub default_factory: Option<Py<PyAny>>,
    pub field_init: bool,
    pub required_error: Option<String>,
    pub none_error: Option<String>,
    pub invalid_error: Option<String>,
}

impl Clone for FieldDescriptor {
    fn clone(&self) -> Self {
        Python::with_gil(|py| FieldDescriptor {
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
            union_variants: self.union_variants.clone(),
            default_value: self.default_value.as_ref().map(|v| v.clone_ref(py)),
            default_factory: self.default_factory.as_ref().map(|f| f.clone_ref(py)),
            field_init: self.field_init,
            required_error: self.required_error.clone(),
            none_error: self.none_error.clone(),
            invalid_error: self.invalid_error.clone(),
        })
    }
}

impl<'py> FromPyObject<'py> for FieldDescriptor {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let py = ob.py();
        let name: String = ob.getattr("name")?.extract()?;
        let name_interned = PyString::intern(py, &name).unbind();
        let serialized_name: Option<String> = ob.getattr("serialized_name")?.extract()?;
        let field_type: FieldType = ob.getattr("field_type")?.extract()?;
        let optional: bool = ob.getattr("optional")?.extract()?;
        let slot_offset: Option<isize> = ob.getattr("slot_offset")?.extract().ok().flatten();

        let nested_schema: Option<SchemaDescriptor> = ob.getattr("nested_schema")?.extract()?;
        let item_schema: Option<FieldDescriptor> = ob.getattr("item_schema")?.extract()?;
        let key_type: Option<FieldType> = ob.getattr("key_type")?.extract()?;
        let value_schema: Option<FieldDescriptor> = ob.getattr("value_schema")?.extract()?;

        let strip_whitespaces: bool = ob.getattr("strip_whitespaces")?.extract().unwrap_or(false);
        let decimal_places: Option<i32> = ob.getattr("decimal_places")?.extract().ok().flatten();
        let decimal_as_string: bool = ob.getattr("decimal_as_string")?.extract().unwrap_or(true);
        let decimal_rounding: Option<Py<PyAny>> = ob.getattr("decimal_rounding")?.extract().ok();
        let datetime_format: Option<String> = ob.getattr("datetime_format")?.extract().ok().flatten();
        let required_error: Option<String> = ob.getattr("required_error")?.extract().ok().flatten();
        let none_error: Option<String> = ob.getattr("none_error")?.extract().ok().flatten();
        let invalid_error: Option<String> = ob.getattr("invalid_error")?.extract().ok().flatten();
        let enum_cls: Option<Py<PyAny>> = ob.getattr("enum_cls")?.extract().ok();
        let union_variants: Option<Vec<FieldDescriptor>> = ob.getattr("union_variants")?.extract().ok();

        let default_value: Option<Py<PyAny>> = ob.getattr("default_value")?.extract().ok();
        let default_factory: Option<Py<PyAny>> = ob.getattr("default_factory")?.extract().ok();
        let field_init: bool = ob.getattr("field_init")?.extract().unwrap_or(true);

        Ok(FieldDescriptor {
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
            union_variants: union_variants.map(|v| v.into_iter().map(Box::new).collect()),
            default_value,
            default_factory,
            field_init,
            required_error,
            none_error,
            invalid_error,
        })
    }
}

#[derive(Debug)]
pub struct SchemaDescriptor {
    pub cls: Py<PyAny>,
    pub fields: Vec<FieldDescriptor>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
}

impl Clone for SchemaDescriptor {
    fn clone(&self) -> Self {
        Python::with_gil(|py| SchemaDescriptor {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
        })
    }
}

impl<'py> FromPyObject<'py> for SchemaDescriptor {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let cls: Py<PyAny> = ob.getattr("cls")?.extract()?;
        let fields: Vec<FieldDescriptor> = ob.getattr("fields")?.extract()?;
        let can_use_direct_slots: bool = ob.getattr("can_use_direct_slots")?.extract().unwrap_or(false);
        let has_post_init: bool = ob.getattr("has_post_init")?.extract().unwrap_or(false);
        Ok(SchemaDescriptor { cls, fields, can_use_direct_slots, has_post_init })
    }
}

#[derive(Clone, Debug, PartialEq)]
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

impl<'py> FromPyObject<'py> for TypeKind {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let s: String = ob.extract()?;
        match s.as_str() {
            "dataclass" => Ok(TypeKind::Dataclass),
            "primitive" => Ok(TypeKind::Primitive),
            "list" => Ok(TypeKind::List),
            "dict" => Ok(TypeKind::Dict),
            "optional" => Ok(TypeKind::Optional),
            "set" => Ok(TypeKind::Set),
            "frozenset" => Ok(TypeKind::FrozenSet),
            "tuple" => Ok(TypeKind::Tuple),
            "union" => Ok(TypeKind::Union),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Unknown type kind: {}", s),
            )),
        }
    }
}

#[derive(Debug)]
pub struct TypeDescriptor {
    pub type_kind: TypeKind,
    pub primitive_type: Option<FieldType>,
    pub optional: bool,
    pub inner_type: Option<Box<TypeDescriptor>>,
    pub item_type: Option<Box<TypeDescriptor>>,
    pub key_type: Option<FieldType>,
    pub value_type: Option<Box<TypeDescriptor>>,
    pub cls: Option<Py<PyAny>>,
    pub fields: Vec<FieldDescriptor>,
    pub union_variants: Option<Vec<Box<TypeDescriptor>>>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
}

impl Clone for TypeDescriptor {
    fn clone(&self) -> Self {
        Python::with_gil(|py| TypeDescriptor {
            type_kind: self.type_kind.clone(),
            primitive_type: self.primitive_type.clone(),
            optional: self.optional,
            inner_type: self.inner_type.clone(),
            item_type: self.item_type.clone(),
            key_type: self.key_type.clone(),
            value_type: self.value_type.clone(),
            cls: self.cls.as_ref().map(|c| c.clone_ref(py)),
            fields: self.fields.clone(),
            union_variants: self.union_variants.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
        })
    }
}

impl<'py> FromPyObject<'py> for TypeDescriptor {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let type_kind: TypeKind = ob.getattr("type_kind")?.extract()?;
        let primitive_type: Option<FieldType> = ob.getattr("primitive_type")?.extract().ok();
        let optional: bool = ob.getattr("optional")?.extract()?;
        let inner_type: Option<TypeDescriptor> = ob.getattr("inner_type")?.extract().ok();
        let item_type: Option<TypeDescriptor> = ob.getattr("item_type")?.extract().ok();
        let key_type: Option<FieldType> = ob.getattr("key_type")?.extract().ok();
        let value_type: Option<TypeDescriptor> = ob.getattr("value_type")?.extract().ok();
        let cls: Option<Py<PyAny>> = ob.getattr("cls")?.extract().ok();
        let fields: Vec<FieldDescriptor> = ob.getattr("fields")?.extract().unwrap_or_default();
        let union_variants: Option<Vec<TypeDescriptor>> = ob.getattr("union_variants")?.extract().ok();
        let can_use_direct_slots: bool = ob.getattr("can_use_direct_slots")?.extract().unwrap_or(false);
        let has_post_init: bool = ob.getattr("has_post_init")?.extract().unwrap_or(false);

        Ok(TypeDescriptor {
            type_kind,
            primitive_type,
            optional,
            inner_type: inner_type.map(Box::new),
            item_type: item_type.map(Box::new),
            key_type,
            value_type: value_type.map(Box::new),
            cls,
            fields,
            union_variants: union_variants.map(|v| v.into_iter().map(Box::new).collect()),
            can_use_direct_slots,
            has_post_init,
        })
    }
}

#[inline]
fn f64_to_json_number(f: f64, field_name: &str) -> PyResult<Value> {
    if f.is_nan() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Cannot serialize NaN float value for field '{}'",
            field_name
        )));
    }
    if f.is_infinite() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Cannot serialize infinite float value for field '{}'",
            field_name
        )));
    }
    Ok(serde_json::Number::from_f64(f)
        .map(Value::Number)
        .expect("f64 should be finite after checks"))
}

#[inline]
fn serialize_value(py: Python, value: &Bound<'_, PyAny>, field: &FieldDescriptor, global_decimal_places: Option<i32>) -> PyResult<Value> {
    if value.is_none() {
        return Ok(Value::Null);
    }

    match field.field_type {
        FieldType::Str => {
            let mut s: String = value.extract()?;
            if field.strip_whitespaces {
                s = s.trim().to_string();
            }
            Ok(Value::String(s))
        }
        FieldType::Int => {
            let i: i64 = value.extract()?;
            Ok(Value::Number(i.into()))
        }
        FieldType::Float => {
            let f: f64 = value.extract()?;
            f64_to_json_number(f, &field.name)
        }
        FieldType::Bool => {
            let b: bool = value.extract()?;
            Ok(Value::Bool(b))
        }
        FieldType::Decimal => {
            let decimal_places = global_decimal_places.or(field.decimal_places);
            let decimal_value = if let Some(places) = decimal_places {
                let cached = get_cached_types(py)?;
                let decimal_cls = cached.decimal_cls.bind(py);
                let quantize_str = format!("0.{}", "0".repeat(places as usize));
                let quantizer = decimal_cls.call1((quantize_str,))?;
                if let Some(ref rounding) = field.decimal_rounding {
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("rounding", rounding.bind(py))?;
                    value.call_method("quantize", (quantizer,), Some(&kwargs))?
                } else {
                    value.call_method1("quantize", (quantizer,))?
                }
            } else {
                value.clone()
            };

            let s: String = decimal_value.str()?.extract()?;
            if field.decimal_as_string {
                Ok(Value::String(s))
            } else {
                let f: f64 = s.parse().map_err(|_| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Cannot parse decimal '{}' as float",
                        s
                    ))
                })?;
                f64_to_json_number(f, &field.name)
            }
        }
        FieldType::Uuid => {
            let s: String = value.str()?.extract()?;
            Ok(Value::String(s))
        }
        FieldType::DateTime => {
            let s: String = if let Some(ref fmt) = field.datetime_format {
                value.call_method1("strftime", (fmt.as_str(),))?.extract()?
            } else {
                value.call_method0("isoformat")?.extract()?
            };
            Ok(Value::String(s))
        }
        FieldType::Date | FieldType::Time => {
            let s: String = value.call_method0("isoformat")?.extract()?;
            Ok(Value::String(s))
        }
        FieldType::List => {
            let list = value.downcast::<PyList>()?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("List field missing item_schema")
            })?;
            let mut items = Vec::with_capacity(list.len());
            for item in list.iter() {
                items.push(serialize_value(py, &item, item_schema, global_decimal_places)?);
            }
            Ok(Value::Array(items))
        }
        FieldType::Dict => {
            let dict = value.downcast::<PyDict>()?;
            let value_schema = field.value_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Dict field missing value_schema")
            })?;
            let mut map = Map::with_capacity(dict.len());
            for (k, v) in dict.iter() {
                let key: String = k.extract()?;
                let val = serialize_value(py, &v, value_schema, global_decimal_places)?;
                map.insert(key, val);
            }
            Ok(Value::Object(map))
        }
        FieldType::Nested => {
            let nested_schema = field.nested_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Nested field missing nested_schema")
            })?;
            serialize_dataclass(py, value, &nested_schema.fields, None, global_decimal_places)
        }
        FieldType::StrEnum => {
            let enum_value = value.getattr("value")?;
            let s: String = enum_value.extract()?;
            Ok(Value::String(s))
        }
        FieldType::IntEnum => {
            let enum_value = value.getattr("value")?;
            let i: i64 = enum_value.extract()?;
            Ok(Value::Number(i.into()))
        }
        FieldType::Set | FieldType::FrozenSet | FieldType::Tuple => {
            let iter = value.try_iter()?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Collection field missing item_schema")
            })?;
            let len_hint = value.len().unwrap_or(0);
            let mut items = Vec::with_capacity(len_hint);
            for item_result in iter {
                let item = item_result?;
                items.push(serialize_value(py, &item, item_schema, global_decimal_places)?);
            }
            Ok(Value::Array(items))
        }
        FieldType::Union => {
            let variants = field.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Union field missing union_variants")
            })?;
            for variant in variants.iter() {
                if let Ok(result) = serialize_value(py, value, variant, global_decimal_places) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Value does not match any union variant for field '{}'",
                field.name
            )))
        }
    }
}

#[inline]
unsafe fn get_slot_value_direct<'py>(
    py: Python<'py>,
    obj: &Bound<'_, PyAny>,
    offset: isize,
) -> Option<Bound<'py, PyAny>> {
    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return None;
    }
    let slot_ptr = (obj_ptr as *const u8).offset(offset) as *const *mut pyo3::ffi::PyObject;
    let py_obj_ptr = *slot_ptr;
    if py_obj_ptr.is_null() {
        return None;
    }
    Some(Py::<PyAny>::from_borrowed_ptr(py, py_obj_ptr).into_bound(py))
}

#[inline]
unsafe fn set_slot_value_direct(
    obj: &Bound<'_, PyAny>,
    offset: isize,
    value: PyObject,
) {
    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return;
    }
    let slot_ptr = (obj_ptr as *mut u8).offset(offset) as *mut *mut pyo3::ffi::PyObject;
    let old_ptr = *slot_ptr;
    let new_ptr = value.into_ptr();
    *slot_ptr = new_ptr;
    if !old_ptr.is_null() {
        pyo3::ffi::Py_DECREF(old_ptr);
    }
}

#[inline]
fn serialize_dataclass(
    py: Python,
    obj: &Bound<'_, PyAny>,
    fields: &[FieldDescriptor],
    none_value_handling: Option<&str>,
    decimal_places: Option<i32>,
) -> PyResult<Value> {
    let mut map = Map::with_capacity(fields.len());
    let ignore_none = none_value_handling.map(|s| s == "ignore").unwrap_or(true);

    for field in fields {
        let py_value = match field.slot_offset {
            Some(offset) => match unsafe { get_slot_value_direct(py, obj, offset) } {
                Some(value) => value,
                None => obj.getattr(field.name.as_str())?,
            },
            None => obj.getattr(field.name.as_str())?,
        };

        if py_value.is_none() && ignore_none {
            continue;
        }

        let json_value = serialize_value(py, &py_value, field, decimal_places)?;
        let key = field.serialized_name.as_ref().unwrap_or(&field.name);
        map.insert(key.clone(), json_value);
    }

    Ok(Value::Object(map))
}

#[inline]
fn serialize_primitive(_py: Python, value: &Bound<'_, PyAny>, field_type: &FieldType) -> PyResult<Value> {
    if value.is_none() {
        return Ok(Value::Null);
    }

    match field_type {
        FieldType::Str => {
            let s: String = value.extract()?;
            Ok(Value::String(s))
        }
        FieldType::Int => {
            let i: i64 = value.extract()?;
            Ok(Value::Number(i.into()))
        }
        FieldType::Float => {
            let f: f64 = value.extract()?;
            f64_to_json_number(f, "float")
        }
        FieldType::Bool => {
            let b: bool = value.extract()?;
            Ok(Value::Bool(b))
        }
        FieldType::Decimal => {
            let s: String = value.str()?.extract()?;
            Ok(Value::String(s))
        }
        FieldType::Uuid => {
            let s: String = value.str()?.extract()?;
            Ok(Value::String(s))
        }
        FieldType::DateTime | FieldType::Date | FieldType::Time => {
            let s: String = value.call_method0("isoformat")?.extract()?;
            Ok(Value::String(s))
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unsupported primitive type",
        )),
    }
}

#[inline]
fn serialize_root_type(
    py: Python,
    value: &Bound<'_, PyAny>,
    descriptor: &TypeDescriptor,
    none_value_handling: Option<&str>,
    decimal_places: Option<i32>,
) -> PyResult<Value> {
    match descriptor.type_kind {
        TypeKind::Dataclass => {
            serialize_dataclass(py, value, &descriptor.fields, none_value_handling, decimal_places)
        }
        TypeKind::Primitive => {
            let field_type = descriptor.primitive_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_type")
            })?;
            serialize_primitive(py, value, field_type)
        }
        TypeKind::List => {
            let list = value.downcast::<PyList>()?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for list")
            })?;
            let mut items = Vec::with_capacity(list.len());
            for item in list.iter() {
                items.push(serialize_root_type(py, &item, item_descriptor, none_value_handling, decimal_places)?);
            }
            Ok(Value::Array(items))
        }
        TypeKind::Dict => {
            let dict = value.downcast::<PyDict>()?;
            let value_descriptor = descriptor.value_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict")
            })?;
            let mut map = Map::with_capacity(dict.len());
            for (k, v) in dict.iter() {
                let key: String = k.extract()?;
                let val = serialize_root_type(py, &v, value_descriptor, none_value_handling, decimal_places)?;
                map.insert(key, val);
            }
            Ok(Value::Object(map))
        }
        TypeKind::Optional => {
            if value.is_none() {
                Ok(Value::Null)
            } else {
                let inner_descriptor = descriptor.inner_type.as_ref().ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type for optional")
                })?;
                serialize_root_type(py, value, inner_descriptor, none_value_handling, decimal_places)
            }
        }
        TypeKind::Set | TypeKind::FrozenSet | TypeKind::Tuple => {
            let iter = value.try_iter()?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for collection")
            })?;
            let len_hint = value.len().unwrap_or(0);
            let mut items = Vec::with_capacity(len_hint);
            for item_result in iter {
                let item = item_result?;
                items.push(serialize_root_type(py, &item, item_descriptor, none_value_handling, decimal_places)?);
            }
            Ok(Value::Array(items))
        }
        TypeKind::Union => {
            let variants = descriptor.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union")
            })?;
            for variant in variants.iter() {
                if let Ok(result) = serialize_root_type(py, value, variant, none_value_handling, decimal_places) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value does not match any union variant"
            ))
        }
    }
}

#[pyfunction]
#[pyo3(signature = (obj, descriptor, none_value_handling=None, decimal_places=None))]
fn dump_to_json(
    py: Python,
    obj: &Bound<'_, PyAny>,
    descriptor: TypeDescriptor,
    none_value_handling: Option<&str>,
    decimal_places: Option<i32>,
) -> PyResult<Py<PyBytes>> {
    let json_value = serialize_root_type(py, obj, &descriptor, none_value_handling, decimal_places)?;
    let json_bytes = serde_json::to_vec(&json_value)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    Ok(PyBytes::new(py, &json_bytes).unbind())
}

#[inline]
fn deserialize_value(
    py: Python,
    value: &Value,
    field: &FieldDescriptor,
) -> PyResult<PyObject> {
    deserialize_value_with_validators(py, value, field, None)
}

fn deserialize_value_with_validators(
    py: Python,
    value: &Value,
    field: &FieldDescriptor,
    validators: Option<&Bound<'_, PyDict>>,
) -> PyResult<PyObject> {
    if value.is_null() {
        if !field.optional {
            let message = field.none_error.as_deref().unwrap_or("Field may not be null.");
            return Err(create_field_validation_error(py, &field.name, message));
        }
        return Ok(py.None());
    }

    match field.field_type {
        FieldType::Str => {
            let mut s = value.as_str().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid string.", field.invalid_error.as_deref())
            })?.to_string();
            if field.strip_whitespaces {
                s = s.trim().to_string();
            }
            s.into_py_any(py)
        }
        FieldType::Int => {
            let i = value.as_i64().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid integer.", field.invalid_error.as_deref())
            })?;
            i.into_py_any(py)
        }
        FieldType::Float => {
            let f = value.as_f64().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid number.", field.invalid_error.as_deref())
            })?;
            f.into_py_any(py)
        }
        FieldType::Bool => {
            let b = value.as_bool().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid boolean.", field.invalid_error.as_deref())
            })?;
            b.into_py_any(py)
        }
        FieldType::Decimal => {
            let decimal_str = if let Some(s) = value.as_str() {
                s.to_string()
            } else if let Some(i) = value.as_i64() {
                i.to_string()
            } else if let Some(f) = value.as_f64() {
                f.to_string()
            } else {
                return Err(create_field_validation_error(py, &field.name, "Not a valid number."));
            };
            let cached = get_cached_types(py)?;
            let decimal_cls = cached.decimal_cls.bind(py);
            let result = decimal_cls.call1((decimal_str,))
                .map_err(|_| create_field_validation_error(py, &field.name, "Not a valid number."))?;
            if let Some(places) = field.decimal_places {
                let quantize_str = format!("1e-{}", places);
                let quantize_val = decimal_cls.call1((quantize_str,))?;
                let quantized = if let Some(ref rounding) = field.decimal_rounding {
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("rounding", rounding.bind(py))?;
                    result.call_method("quantize", (quantize_val,), Some(&kwargs))?
                } else {
                    result.call_method1("quantize", (quantize_val,))?
                };
                return Ok(quantized.unbind());
            }
            Ok(result.unbind())
        }
        FieldType::Uuid => {
            let s = value.as_str().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid UUID.", field.invalid_error.as_deref())
            })?;
            let cached = get_cached_types(py)?;
            cached.uuid_cls.bind(py).call1((s,))
                .map(|uuid_obj| uuid_obj.unbind())
                .map_err(|_| create_field_validation_error(py, &field.name, "Not a valid UUID."))
        }
        FieldType::DateTime => {
            let s = value.as_str().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid datetime.", field.invalid_error.as_deref())
            })?;
            let cached = get_cached_types(py)?;
            let datetime_cls = cached.datetime_cls.bind(py);
            let result = if let Some(ref fmt) = field.datetime_format {
                datetime_cls.call_method1("strptime", (s, fmt.as_str()))
            } else {
                datetime_cls.call_method1("fromisoformat", (s,))
            };
            let dt = result.map_err(|_| create_field_validation_error(py, &field.name, "Not a valid datetime."))?;
            let tzinfo = dt.getattr("tzinfo")?;
            if tzinfo.is_none() {
                let kwargs = PyDict::new(py);
                kwargs.set_item("tzinfo", cached.utc_tz.bind(py))?;
                Ok(dt.call_method("replace", (), Some(&kwargs))?.unbind())
            } else {
                Ok(dt.unbind())
            }
        }
        FieldType::Date => {
            let s = value.as_str().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid date.", field.invalid_error.as_deref())
            })?;
            let cached = get_cached_types(py)?;
            cached.date_cls.bind(py).call_method1("fromisoformat", (s,))
                .map(|date_obj| date_obj.unbind())
                .map_err(|_| create_field_validation_error(py, &field.name, "Not a valid date."))
        }
        FieldType::Time => {
            let s = value.as_str().ok_or_else(|| {
                create_field_validation_error_with_custom(py, &field.name, "Not a valid time.", field.invalid_error.as_deref())
            })?;
            let cached = get_cached_types(py)?;
            cached.time_cls.bind(py).call_method1("fromisoformat", (s,))
                .map(|time_obj| time_obj.unbind())
                .map_err(|_| create_field_validation_error(py, &field.name, "Not a valid time."))
        }
        FieldType::List => {
            let arr = value.as_array().ok_or_else(|| {
                create_field_validation_error(py, &field.name, "Not a valid list.")
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("List field missing item_schema")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            let item_validator_key = format!("{}.__item__", field.name);
            for item in arr.iter() {
                let py_item = deserialize_value(py, item, item_schema)?;
                if let Some(v) = validators {
                    if let Ok(Some(item_validators)) = v.get_item(&item_validator_key) {
                        let validator_list: &Bound<'_, PyList> = item_validators.downcast()?;
                        for validator in validator_list.iter() {
                            let result = validator.call1((py_item.bind(py),))?;
                            if !result.is_truthy()? {
                                return Err(create_validation_error(py, &field.name, "Validation failed."));
                            }
                        }
                    }
                }
                items.push(py_item);
            }
            Ok(PyList::new(py, items)?.unbind().into())
        }
        FieldType::Dict => {
            let obj = value.as_object().ok_or_else(|| {
                create_field_validation_error(py, &field.name, "Not a valid dict.")
            })?;
            let value_schema = field.value_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Dict field missing value_schema")
            })?;
            let dict = PyDict::new(py);
            for (k, v) in obj {
                let py_value = deserialize_value(py, v, value_schema)?;
                dict.set_item(k, py_value)?;
            }
            Ok(dict.unbind().into())
        }
        FieldType::Nested => {
            let obj = value.as_object().ok_or_else(|| {
                create_field_validation_error(py, &field.name, "Not a valid nested object.")
            })?;
            let nested_schema = field.nested_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Nested field missing nested_schema")
            })?;
            let cls = nested_schema.cls.bind(py);
            if nested_schema.can_use_direct_slots {
                deserialize_dataclass_direct_slots(py, obj, &nested_schema.fields, cls, None, None)
            } else {
                deserialize_dataclass(py, obj, &nested_schema.fields, &nested_schema.cls)
            }
        }
        FieldType::StrEnum => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected string for str enum field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let enum_cls = field.enum_cls.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("StrEnum field missing enum_cls")
            })?;
            Ok(enum_cls.call(py, (s,), None)?)
        }
        FieldType::IntEnum => {
            let i = value.as_i64().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected integer for int enum field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let enum_cls = field.enum_cls.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("IntEnum field missing enum_cls")
            })?;
            Ok(enum_cls.call(py, (i,), None)?)
        }
        FieldType::Set => {
            let arr = value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected array for set field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Set field missing item_schema")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            let item_validator_key = format!("{}.__item__", field.name);
            for item in arr.iter() {
                let py_item = deserialize_value(py, item, item_schema)?;
                if let Some(v) = validators {
                    if let Ok(Some(item_validators)) = v.get_item(&item_validator_key) {
                        let validator_list: &Bound<'_, PyList> = item_validators.downcast()?;
                        for validator in validator_list.iter() {
                            let result = validator.call1((py_item.bind(py),))?;
                            if !result.is_truthy()? {
                                return Err(create_validation_error(py, &field.name, "Validation failed."));
                            }
                        }
                    }
                }
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.set_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        FieldType::FrozenSet => {
            let arr = value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected array for frozenset field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("FrozenSet field missing item_schema")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for item in arr.iter() {
                items.push(deserialize_value(py, item, item_schema)?);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.frozenset_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        FieldType::Tuple => {
            let arr = value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected array for tuple field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Tuple field missing item_schema")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            let item_validator_key = format!("{}.__item__", field.name);
            for item in arr.iter() {
                let py_item = deserialize_value(py, item, item_schema)?;
                if let Some(v) = validators {
                    if let Ok(Some(item_validators)) = v.get_item(&item_validator_key) {
                        let validator_list: &Bound<'_, PyList> = item_validators.downcast()?;
                        for validator in validator_list.iter() {
                            let result = validator.call1((py_item.bind(py),))?;
                            if !result.is_truthy()? {
                                return Err(create_validation_error(py, &field.name, "Validation failed."));
                            }
                        }
                    }
                }
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.tuple_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        FieldType::Union => {
            let variants = field.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Union field missing union_variants")
            })?;
            for variant in variants.iter() {
                if let Ok(result) = deserialize_value(py, value, variant) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Value does not match any union variant for field '{}'",
                field.name
            )))
        }
    }
}

#[cold]
#[inline(never)]
fn wrap_error_with_field(py: Python, inner: PyErr, field_name: &str) -> PyErr {
    let inner_value = inner.value(py);
    if let Ok(inner_dict) = inner_value.downcast::<PyDict>() {
        if inner_dict.contains(field_name).unwrap_or(false) {
            return inner;
        }
        let outer_dict = PyDict::new(py);
        let _ = outer_dict.set_item(field_name, inner_dict);
        PyErr::new::<pyo3::exceptions::PyValueError, _>(outer_dict.into_any().unbind())
    } else if let Ok(args) = inner_value.getattr("args") {
        if let Ok(first_arg) = args.get_item(0) {
            if let Ok(inner_dict) = first_arg.downcast::<PyDict>() {
                if inner_dict.contains(field_name).unwrap_or(false) {
                    return inner;
                }
                let outer_dict = PyDict::new(py);
                let _ = outer_dict.set_item(field_name, inner_dict);
                return PyErr::new::<pyo3::exceptions::PyValueError, _>(outer_dict.into_any().unbind());
            }
        }
        inner
    } else {
        inner
    }
}

#[cold]
#[inline(never)]
fn missing_field_error(py: Python, field_name: &str, custom_message: Option<&str>) -> PyErr {
    let dict = PyDict::new(py);
    let message = custom_message.unwrap_or("Missing data for required field.");
    let error_list = PyList::new(py, vec![message]).unwrap();
    let _ = dict.set_item(field_name, error_list);
    let py_obj: PyObject = dict.unbind().into();
    PyErr::new::<pyo3::exceptions::PyValueError, _>(py_obj)
}

#[inline]
fn deserialize_primitive(py: Python, value: &Value, field_type: &FieldType) -> PyResult<PyObject> {
    if value.is_null() {
        return Ok(py.None());
    }

    match field_type {
        FieldType::Str => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string")
            })?;
            s.into_py_any(py)
        }
        FieldType::Int => {
            let i = value.as_i64().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected integer")
            })?;
            i.into_py_any(py)
        }
        FieldType::Float => {
            let f = value.as_f64().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected float")
            })?;
            f.into_py_any(py)
        }
        FieldType::Bool => {
            let b = value.as_bool().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected boolean")
            })?;
            b.into_py_any(py)
        }
        FieldType::Decimal => {
            let decimal_str = if let Some(s) = value.as_str() {
                s.to_string()
            } else if let Some(i) = value.as_i64() {
                i.to_string()
            } else if let Some(f) = value.as_f64() {
                f.to_string()
            } else {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Expected string or number for decimal"
                ));
            };
            let cached = get_cached_types(py)?;
            Ok(cached.decimal_cls.bind(py).call1((decimal_str,))?.unbind())
        }
        FieldType::Uuid => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string for uuid")
            })?;
            let cached = get_cached_types(py)?;
            Ok(cached.uuid_cls.bind(py).call1((s,))?.unbind())
        }
        FieldType::DateTime => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string for datetime")
            })?;
            let cached = get_cached_types(py)?;
            Ok(cached.datetime_cls.bind(py).call_method1("fromisoformat", (s,))?.unbind())
        }
        FieldType::Date => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string for date")
            })?;
            let cached = get_cached_types(py)?;
            Ok(cached.date_cls.bind(py).call_method1("fromisoformat", (s,))?.unbind())
        }
        FieldType::Time => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string for time")
            })?;
            let cached = get_cached_types(py)?;
            Ok(cached.time_cls.bind(py).call_method1("fromisoformat", (s,))?.unbind())
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unsupported primitive type",
        )),
    }
}

#[inline]
fn deserialize_dataclass(
    py: Python,
    json_obj: &Map<String, Value>,
    fields: &[FieldDescriptor],
    cls: &Py<PyAny>,
) -> PyResult<PyObject> {
    let kwargs = PyDict::new(py);

    for field in fields {
        let key = field.serialized_name.as_ref().unwrap_or(&field.name);
        if let Some(json_field) = json_obj.get(key) {
            let py_value = if field.field_type == FieldType::Nested {
                let nested_schema = field.nested_schema.as_ref().unwrap();
                let nested_obj = json_field.as_object().ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object for nested field")
                })?;
                deserialize_dataclass(py, nested_obj, &nested_schema.fields, &nested_schema.cls)
                    .map_err(|e| wrap_error_with_field(py, e, &field.name))?
            } else {
                deserialize_value(py, json_field, field)
                    .map_err(|e| wrap_error_with_field(py, e, &field.name))?
            };
            kwargs.set_item(field.name_interned.bind(py), py_value)?;
        } else if !field.optional {
            return Err(missing_field_error(py, &field.name, field.required_error.as_deref()));
        }
    }

    cls.call(py, (), Some(&kwargs))
}

#[inline]
fn deserialize_root_type(
    py: Python,
    json_value: &Value,
    descriptor: &TypeDescriptor,
) -> PyResult<PyObject> {
    match descriptor.type_kind {
        TypeKind::Dataclass => {
            let obj = json_value.as_object().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object")
            })?;
            let cls = descriptor.cls.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing cls for dataclass")
            })?;
            deserialize_dataclass(py, obj, &descriptor.fields, cls)
        }
        TypeKind::Primitive => {
            let field_type = descriptor.primitive_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_type")
            })?;
            deserialize_primitive(py, json_value, field_type)
        }
        TypeKind::List => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array")
            })?;

            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for list")
            })?;

            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type(py, item, item_descriptor)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }

            Ok(PyList::new(py, items)?.unbind().into())
        }
        TypeKind::Dict => {
            let obj = json_value.as_object().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object")
            })?;

            let value_descriptor = descriptor.value_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict")
            })?;

            let dict = PyDict::new(py);
            for (k, v) in obj {
                let val = deserialize_root_type(py, v, value_descriptor)
                    .map_err(|e| wrap_error_with_field(py, e, k))?;
                dict.set_item(k, val)?;
            }
            Ok(dict.unbind().into())
        }
        TypeKind::Optional => {
            if json_value.is_null() {
                Ok(py.None())
            } else {
                let inner_descriptor = descriptor.inner_type.as_ref().ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type for optional")
                })?;
                deserialize_root_type(py, json_value, inner_descriptor)
            }
        }
        TypeKind::Set => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array for set")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for set")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type(py, item, item_descriptor)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.set_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        TypeKind::FrozenSet => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array for frozenset")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for frozenset")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type(py, item, item_descriptor)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.frozenset_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        TypeKind::Tuple => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array for tuple")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for tuple")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type(py, item, item_descriptor)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.tuple_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        TypeKind::Union => {
            let variants = descriptor.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union")
            })?;
            for variant in variants.iter() {
                if let Ok(result) = deserialize_root_type(py, json_value, variant) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value does not match any union variant"
            ))
        }
    }
}

#[pyfunction]
#[pyo3(signature = (json_bytes, descriptor))]
fn load_from_json(
    py: Python,
    json_bytes: &[u8],
    descriptor: TypeDescriptor,
) -> PyResult<PyObject> {
    let json_value: Value = serde_json::from_slice(json_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    deserialize_root_type(py, &json_value, &descriptor)
}

#[pyfunction]
#[pyo3(signature = (schema_id, raw_schema))]
fn register_schema(_py: Python, schema_id: u64, raw_schema: &Bound<'_, PyDict>) -> PyResult<()> {
    let descriptor = build_type_descriptor_from_dict(raw_schema)?;
    let mut cache = SCHEMA_CACHE.write().unwrap_or_else(|e| e.into_inner());
    cache.insert(schema_id, descriptor);
    Ok(())
}

fn build_type_descriptor_from_dict(raw: &Bound<'_, PyDict>) -> PyResult<TypeDescriptor> {
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
                .map(|v| v.extract().unwrap_or(false))
                .unwrap_or(false);

            let has_post_init: bool = raw.get_item("has_post_init")?
                .map(|v| v.extract().unwrap_or(false))
                .unwrap_or(false);

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
                union_variants: None,
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        "union" => {
            let variants_raw: Vec<Bound<'_, PyDict>> = raw.get_item("union_variants")?.ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union")
            })?.extract()?;
            let variants: Vec<Box<TypeDescriptor>> = variants_raw
                .iter()
                .map(|v| build_type_descriptor_from_dict(v).map(Box::new))
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
                union_variants: Some(variants),
                can_use_direct_slots: false,
                has_post_init: false,
            })
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown type_kind: {}", type_kind)
        )),
    }
}

fn parse_field_type(s: &str) -> PyResult<FieldType> {
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
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown field type: {}", s)
        )),
    }
}

fn build_field_from_dict(raw: &Bound<'_, PyDict>) -> PyResult<FieldDescriptor> {
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
        .map(|v| v.extract().unwrap_or(false))
        .unwrap_or(false);

    let slot_offset: Option<isize> = raw.get_item("slot_offset")?
        .and_then(|v| v.extract().ok());

    let strip_whitespaces: bool = raw.get_item("strip_whitespaces")?
        .map(|v| v.extract().unwrap_or(false))
        .unwrap_or(false);

    let decimal_places: Option<i32> = raw.get_item("decimal_places")?
        .and_then(|v| v.extract().ok());

    let decimal_as_string: bool = raw.get_item("decimal_as_string")?
        .map(|v| v.extract().unwrap_or(true))
        .unwrap_or(true);

    let datetime_format: Option<String> = raw.get_item("datetime_format")?
        .and_then(|v| v.extract().ok());

    let nested_schema: Option<Box<SchemaDescriptor>> = if let Some(nested_raw) = raw.get_item("nested_schema")? {
        if !nested_raw.is_none() {
            let nested_dict: Bound<'_, PyDict> = nested_raw.extract()?;
            Some(Box::new(build_schema_from_dict(&nested_dict)?))
        } else {
            None
        }
    } else {
        None
    };

    let item_schema: Option<Box<FieldDescriptor>> = if let Some(item_raw) = raw.get_item("item_schema")? {
        if !item_raw.is_none() {
            let item_dict: Bound<'_, PyDict> = item_raw.extract()?;
            Some(Box::new(build_field_from_dict(&item_dict)?))
        } else {
            None
        }
    } else {
        None
    };

    let key_type: Option<FieldType> = if let Some(kt) = raw.get_item("key_type")? {
        if !kt.is_none() {
            let kt_str: String = kt.extract()?;
            Some(parse_field_type(&kt_str)?)
        } else {
            None
        }
    } else {
        None
    };

    let value_schema: Option<Box<FieldDescriptor>> = if let Some(value_raw) = raw.get_item("value_schema")? {
        if !value_raw.is_none() {
            let value_dict: Bound<'_, PyDict> = value_raw.extract()?;
            Some(Box::new(build_field_from_dict(&value_dict)?))
        } else {
            None
        }
    } else {
        None
    };

    let enum_cls: Option<Py<PyAny>> = if let Some(cls_raw) = raw.get_item("enum_cls")? {
        if !cls_raw.is_none() {
            Some(cls_raw.extract()?)
        } else {
            None
        }
    } else {
        None
    };

    let union_variants: Option<Vec<Box<FieldDescriptor>>> = if let Some(variants_raw) = raw.get_item("union_variants")? {
        if !variants_raw.is_none() {
            let variants_list: Vec<Bound<'_, PyDict>> = variants_raw.extract()?;
            let variants: Vec<Box<FieldDescriptor>> = variants_list
                .iter()
                .map(|v| build_field_from_dict(v).map(Box::new))
                .collect::<PyResult<_>>()?;
            Some(variants)
        } else {
            None
        }
    } else {
        None
    };

    let default_value: Option<Py<PyAny>> = if let Some(dv) = raw.get_item("default_value")? {
        if !dv.is_none() {
            Some(dv.extract()?)
        } else {
            None
        }
    } else {
        None
    };

    let default_factory: Option<Py<PyAny>> = if let Some(df) = raw.get_item("default_factory")? {
        if !df.is_none() {
            Some(df.extract()?)
        } else {
            None
        }
    } else {
        None
    };

    let decimal_rounding: Option<Py<PyAny>> = if let Some(dr) = raw.get_item("decimal_rounding")? {
        if !dr.is_none() {
            Some(dr.extract()?)
        } else {
            None
        }
    } else {
        None
    };

    let required_error: Option<String> = raw.get_item("required_error")?.and_then(|v| v.extract().ok());
    let none_error: Option<String> = raw.get_item("none_error")?.and_then(|v| v.extract().ok());
    let invalid_error: Option<String> = raw.get_item("invalid_error")?.and_then(|v| v.extract().ok());

    let field_init: bool = raw.get_item("field_init")?
        .map(|v| v.extract().unwrap_or(true))
        .unwrap_or(true);

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
        union_variants,
        default_value,
        default_factory,
        field_init,
        required_error,
        none_error,
        invalid_error,
    })
}

fn build_schema_from_dict(raw: &Bound<'_, PyDict>) -> PyResult<SchemaDescriptor> {
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
        .map(|v| v.extract().unwrap_or(false))
        .unwrap_or(false);

    let has_post_init: bool = raw.get_item("has_post_init")?
        .map(|v| v.extract().unwrap_or(false))
        .unwrap_or(false);

    Ok(SchemaDescriptor { cls, fields, can_use_direct_slots, has_post_init })
}

#[pyfunction]
#[pyo3(signature = (schema_id, obj, none_value_handling=None, validators=None, decimal_places=None, encoding="utf-8"))]
fn dump_cached(
    py: Python,
    schema_id: u64,
    obj: &Bound<'_, PyAny>,
    none_value_handling: Option<&str>,
    validators: Option<&Bound<'_, PyDict>>,
    decimal_places: Option<i32>,
    encoding: &str,
) -> PyResult<Py<PyBytes>> {
    let cache = SCHEMA_CACHE.read().unwrap_or_else(|e| e.into_inner());
    let descriptor = cache.get(&schema_id).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Schema {} not registered", schema_id))
    })?;

    if let Some(v) = validators {
        validate_object(py, obj, descriptor, v)?;
    }

    let json_value = serialize_root_type(py, obj, descriptor, none_value_handling, decimal_places)?;
    let json_bytes = serde_json::to_vec(&json_value)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let output_bytes = encode_from_utf8_bytes(&json_bytes, encoding)?;
    Ok(PyBytes::new(py, &output_bytes).unbind())
}

fn validate_object(
    _py: Python,
    obj: &Bound<'_, PyAny>,
    descriptor: &TypeDescriptor,
    validators: &Bound<'_, PyDict>,
) -> PyResult<()> {
    for field in &descriptor.fields {
        if let Some(field_validators) = validators.get_item(&field.name)? {
            let py_value = obj.getattr(field.name.as_str())?;
            let validator_list: &Bound<'_, PyList> = field_validators.downcast()?;
            for validator in validator_list.iter() {
                validator.call1((&py_value,))?;
            }
        }
    }
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (schema_id, json_bytes, post_loads=None, validators=None, encoding="utf-8"))]
fn load_cached(
    py: Python,
    schema_id: u64,
    json_bytes: &[u8],
    post_loads: Option<&Bound<'_, PyDict>>,
    validators: Option<&Bound<'_, PyDict>>,
    encoding: &str,
) -> PyResult<PyObject> {
    let cache = SCHEMA_CACHE.read().unwrap_or_else(|e| e.into_inner());
    let descriptor = cache.get(&schema_id).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Schema {} not registered", schema_id))
    })?;

    let utf8_bytes = decode_to_utf8_bytes(json_bytes, encoding)?;
    let json_value: Value = serde_json::from_slice(&utf8_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    deserialize_root_type_cached(py, &json_value, descriptor, post_loads, validators)
}

fn deserialize_root_type_cached(
    py: Python,
    json_value: &Value,
    descriptor: &TypeDescriptor,
    post_loads: Option<&Bound<'_, PyDict>>,
    validators: Option<&Bound<'_, PyDict>>,
) -> PyResult<PyObject> {
    match descriptor.type_kind {
        TypeKind::Dataclass => {
            let obj = json_value.as_object().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object")
            })?;
            let cls = descriptor.cls.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing cls for dataclass")
            })?;
            if descriptor.can_use_direct_slots {
                deserialize_dataclass_direct_slots(py, obj, &descriptor.fields, cls.bind(py), post_loads, validators)
            } else {
                deserialize_dataclass_cached(py, obj, &descriptor.fields, cls.bind(py), post_loads, validators)
            }
        }
        TypeKind::Primitive => {
            let field_type = descriptor.primitive_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_type")
            })?;
            deserialize_primitive(py, json_value, field_type)
        }
        TypeKind::List => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for list")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type_cached(py, item, item_descriptor, post_loads, validators)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }
            Ok(PyList::new(py, items)?.unbind().into())
        }
        TypeKind::Dict => {
            let obj = json_value.as_object().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object")
            })?;
            let value_descriptor = descriptor.value_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict")
            })?;
            let dict = PyDict::new(py);
            for (k, v) in obj {
                let val = deserialize_root_type_cached(py, v, value_descriptor, post_loads, validators)
                    .map_err(|e| wrap_error_with_field(py, e, k))?;
                dict.set_item(k, val)?;
            }
            Ok(dict.unbind().into())
        }
        TypeKind::Optional => {
            if json_value.is_null() {
                Ok(py.None())
            } else {
                let inner_descriptor = descriptor.inner_type.as_ref().ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type for optional")
                })?;
                deserialize_root_type_cached(py, json_value, inner_descriptor, post_loads, validators)
            }
        }
        TypeKind::Set => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array for set")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for set")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type_cached(py, item, item_descriptor, post_loads, validators)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.set_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        TypeKind::FrozenSet => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array for frozenset")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for frozenset")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type_cached(py, item, item_descriptor, post_loads, validators)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.frozenset_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        TypeKind::Tuple => {
            let arr = json_value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON array for tuple")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for tuple")
            })?;
            let mut items = Vec::with_capacity(arr.len());
            for (idx, item) in arr.iter().enumerate() {
                let py_item = deserialize_root_type_cached(py, item, item_descriptor, post_loads, validators)
                    .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))?;
                items.push(py_item);
            }
            let cached = get_cached_types(py)?;
            Ok(cached.tuple_cls.bind(py).call1((PyList::new(py, items)?,))?.unbind())
        }
        TypeKind::Union => {
            let variants = descriptor.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union")
            })?;
            for variant in variants.iter() {
                if let Ok(result) = deserialize_root_type_cached(py, json_value, variant, post_loads, validators) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value does not match any union variant"
            ))
        }
    }
}

fn deserialize_dataclass_direct_slots(
    py: Python,
    json_obj: &Map<String, Value>,
    fields: &[FieldDescriptor],
    cls: &Bound<'_, PyAny>,
    post_loads: Option<&Bound<'_, PyDict>>,
    validators: Option<&Bound<'_, PyDict>>,
) -> PyResult<PyObject> {
    let cached_types = get_cached_types(py)?;
    let object_type = cached_types.object_cls.bind(py);
    let instance = object_type.call_method1("__new__", (cls,))?;

    for field in fields {
        let key = field.serialized_name.as_ref().unwrap_or(&field.name);

        let py_value = if let Some(json_field) = json_obj.get(key) {
            let mut value = if field.field_type == FieldType::Nested {
                let nested_schema = field.nested_schema.as_ref().unwrap();
                let nested_obj = json_field.as_object().ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object for nested field")
                })?;
                let nested_cls = nested_schema.cls.bind(py);
                if nested_schema.can_use_direct_slots {
                    deserialize_dataclass_direct_slots(py, nested_obj, &nested_schema.fields, nested_cls, post_loads, validators)
                        .map_err(|e| wrap_error_with_field(py, e, &field.name))?
                } else {
                    deserialize_dataclass_cached(py, nested_obj, &nested_schema.fields, nested_cls, post_loads, validators)
                        .map_err(|e| wrap_error_with_field(py, e, &field.name))?
                }
            } else {
                deserialize_value_with_validators(py, json_field, field, validators)
                    .map_err(|e| wrap_error_with_field(py, e, &field.name))?
            };

            if let Some(pl) = post_loads {
                if let Some(post_load_fn) = pl.get_item(&field.name)? {
                    if !post_load_fn.is_none() {
                        value = post_load_fn.call1((value,))?.unbind();
                    }
                }
            }

            if let Some(v) = validators {
                if let Some(field_validators) = v.get_item(&field.name)? {
                    let validator_list: &Bound<'_, PyList> = field_validators.downcast()?;
                    for validator in validator_list.iter() {
                        let result = validator.call1((value.bind(py),))?;
                        if !result.is_truthy()? {
                            return Err(create_validation_error(py, &field.name, "Validation failed."));
                        }
                    }
                }
            }

            value
        } else if let Some(ref default_factory) = field.default_factory {
            default_factory.call0(py)?
        } else if let Some(ref default_value) = field.default_value {
            default_value.clone_ref(py)
        } else if field.optional {
            py.None()
        } else {
            return Err(missing_field_error(py, &field.name, field.required_error.as_deref()));
        };

        if let Some(offset) = field.slot_offset {
            unsafe {
                set_slot_value_direct(&instance, offset, py_value);
            }
        } else {
            instance.setattr(field.name_interned.bind(py), py_value)?;
        }
    }

    Ok(instance.unbind())
}

fn deserialize_dataclass_cached(
    py: Python,
    json_obj: &Map<String, Value>,
    fields: &[FieldDescriptor],
    cls: &Bound<'_, PyAny>,
    post_loads: Option<&Bound<'_, PyDict>>,
    validators: Option<&Bound<'_, PyDict>>,
) -> PyResult<PyObject> {
    let kwargs = PyDict::new(py);

    for field in fields {
        let key = field.serialized_name.as_ref().unwrap_or(&field.name);
        if let Some(json_field) = json_obj.get(key) {
            let mut py_value = if field.field_type == FieldType::Nested {
                let nested_schema = field.nested_schema.as_ref().unwrap();
                let nested_obj = json_field.as_object().ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object for nested field")
                })?;
                let nested_cls = nested_schema.cls.bind(py);
                deserialize_dataclass_cached(py, nested_obj, &nested_schema.fields, nested_cls, post_loads, validators)
                    .map_err(|e| wrap_error_with_field(py, e, &field.name))?
            } else {
                deserialize_value_with_validators(py, json_field, field, validators)
                    .map_err(|e| wrap_error_with_field(py, e, &field.name))?
            };

            if let Some(pl) = post_loads {
                if let Some(post_load_fn) = pl.get_item(&field.name)? {
                    if !post_load_fn.is_none() {
                        py_value = post_load_fn.call1((py_value,))?.unbind();
                    }
                }
            }

            if let Some(v) = validators {
                if let Some(field_validators) = v.get_item(&field.name)? {
                    let validator_list: &Bound<'_, PyList> = field_validators.downcast()?;
                    for validator in validator_list.iter() {
                        let result = validator.call1((py_value.bind(py),))?;
                        if !result.is_truthy()? {
                            return Err(create_validation_error(py, &field.name, "Validation failed."));
                        }
                    }
                }
            }

            kwargs.set_item(field.name_interned.bind(py), py_value)?;
        } else if !field.optional {
            return Err(missing_field_error(py, &field.name, field.required_error.as_deref()));
        }
    }

    cls.call((), Some(&kwargs))?.extract()
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(dump_to_json, m)?)?;
    m.add_function(wrap_pyfunction!(load_from_json, m)?)?;
    m.add_function(wrap_pyfunction!(register_schema, m)?)?;
    m.add_function(wrap_pyfunction!(dump_cached, m)?)?;
    m.add_function(wrap_pyfunction!(load_cached, m)?)?;
    Ok(())
}
