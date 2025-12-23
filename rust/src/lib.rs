use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList};
use serde_json::{Map, Value};

#[derive(Clone, Debug, PartialEq)]
pub enum FieldType {
    Str,
    Int,
    Float,
    Bool,
    List,
    Dict,
    Nested,
}

impl<'py> FromPyObject<'py> for FieldType {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let s: String = ob.extract()?;
        match s.as_str() {
            "str" => Ok(FieldType::Str),
            "int" => Ok(FieldType::Int),
            "float" => Ok(FieldType::Float),
            "bool" => Ok(FieldType::Bool),
            "list" => Ok(FieldType::List),
            "dict" => Ok(FieldType::Dict),
            "nested" => Ok(FieldType::Nested),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Unknown field type: {}", s),
            )),
        }
    }
}

#[derive(Clone, Debug)]
pub struct FieldDescriptor {
    pub name: String,
    pub serialized_name: Option<String>,
    pub field_type: FieldType,
    pub optional: bool,
    pub nested_schema: Option<Box<SchemaDescriptor>>,
    pub item_schema: Option<Box<FieldDescriptor>>,
    pub key_type: Option<FieldType>,
    pub value_schema: Option<Box<FieldDescriptor>>,
}

impl<'py> FromPyObject<'py> for FieldDescriptor {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let name: String = ob.getattr("name")?.extract()?;
        let serialized_name: Option<String> = ob.getattr("serialized_name")?.extract()?;
        let field_type: FieldType = ob.getattr("field_type")?.extract()?;
        let optional: bool = ob.getattr("optional")?.extract()?;

        let nested_schema: Option<SchemaDescriptor> = ob.getattr("nested_schema")?.extract()?;
        let item_schema: Option<FieldDescriptor> = ob.getattr("item_schema")?.extract()?;
        let key_type: Option<FieldType> = ob.getattr("key_type")?.extract()?;
        let value_schema: Option<FieldDescriptor> = ob.getattr("value_schema")?.extract()?;

        Ok(FieldDescriptor {
            name,
            serialized_name,
            field_type,
            optional,
            nested_schema: nested_schema.map(Box::new),
            item_schema: item_schema.map(Box::new),
            key_type,
            value_schema: value_schema.map(Box::new),
        })
    }
}

#[derive(Debug)]
pub struct SchemaDescriptor {
    pub cls: Py<PyAny>,
    pub fields: Vec<FieldDescriptor>,
}

impl Clone for SchemaDescriptor {
    fn clone(&self) -> Self {
        Python::with_gil(|py| SchemaDescriptor {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
        })
    }
}

impl<'py> FromPyObject<'py> for SchemaDescriptor {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let cls: Py<PyAny> = ob.getattr("cls")?.extract()?;
        let fields: Vec<FieldDescriptor> = ob.getattr("fields")?.extract()?;
        Ok(SchemaDescriptor { cls, fields })
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum TypeKind {
    Dataclass,
    Primitive,
    List,
    Dict,
    Optional,
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
        })
    }
}

fn serialize_value(py: Python, value: &Bound<'_, PyAny>, field: &FieldDescriptor) -> PyResult<Value> {
    if value.is_none() {
        return Ok(Value::Null);
    }

    match field.field_type {
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
            Ok(serde_json::Number::from_f64(f)
                .map(Value::Number)
                .unwrap_or(Value::Null))
        }
        FieldType::Bool => {
            let b: bool = value.extract()?;
            Ok(Value::Bool(b))
        }
        FieldType::List => {
            let list = value.downcast::<PyList>()?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("List field missing item_schema")
            })?;
            let items: Vec<Value> = list
                .iter()
                .map(|item| serialize_value(py, &item, item_schema))
                .collect::<PyResult<_>>()?;
            Ok(Value::Array(items))
        }
        FieldType::Dict => {
            let dict = value.downcast::<PyDict>()?;
            let value_schema = field.value_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Dict field missing value_schema")
            })?;
            let mut map = Map::new();
            for (k, v) in dict.iter() {
                let key: String = k.extract()?;
                let val = serialize_value(py, &v, value_schema)?;
                map.insert(key, val);
            }
            Ok(Value::Object(map))
        }
        FieldType::Nested => {
            let nested_schema = field.nested_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Nested field missing nested_schema")
            })?;
            serialize_dataclass(py, value, &nested_schema.fields, None)
        }
    }
}

fn serialize_dataclass(
    py: Python,
    obj: &Bound<'_, PyAny>,
    fields: &[FieldDescriptor],
    none_value_handling: Option<&str>,
) -> PyResult<Value> {
    let mut map = Map::new();
    let ignore_none = none_value_handling.map(|s| s == "ignore").unwrap_or(true);

    for field in fields {
        let py_value = obj.getattr(field.name.as_str())?;

        if py_value.is_none() && ignore_none {
            continue;
        }

        let serialized_name = field.serialized_name.as_ref().unwrap_or(&field.name);
        let json_value = serialize_value(py, &py_value, field)?;
        map.insert(serialized_name.clone(), json_value);
    }

    Ok(Value::Object(map))
}

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
            Ok(serde_json::Number::from_f64(f)
                .map(Value::Number)
                .unwrap_or(Value::Null))
        }
        FieldType::Bool => {
            let b: bool = value.extract()?;
            Ok(Value::Bool(b))
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unsupported primitive type",
        )),
    }
}

fn serialize_root_type(
    py: Python,
    value: &Bound<'_, PyAny>,
    descriptor: &TypeDescriptor,
    none_value_handling: Option<&str>,
) -> PyResult<Value> {
    match descriptor.type_kind {
        TypeKind::Dataclass => {
            serialize_dataclass(py, value, &descriptor.fields, none_value_handling)
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
            let items: Vec<Value> = list
                .iter()
                .map(|item| serialize_root_type(py, &item, item_descriptor, none_value_handling))
                .collect::<PyResult<_>>()?;
            Ok(Value::Array(items))
        }
        TypeKind::Dict => {
            let dict = value.downcast::<PyDict>()?;
            let value_descriptor = descriptor.value_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict")
            })?;
            let mut map = Map::new();
            for (k, v) in dict.iter() {
                let key: String = k.extract()?;
                let val = serialize_root_type(py, &v, value_descriptor, none_value_handling)?;
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
                serialize_root_type(py, value, inner_descriptor, none_value_handling)
            }
        }
    }
}

#[pyfunction]
#[pyo3(signature = (obj, descriptor, none_value_handling=None))]
fn dump_to_json(
    py: Python,
    obj: &Bound<'_, PyAny>,
    descriptor: TypeDescriptor,
    none_value_handling: Option<&str>,
) -> PyResult<Py<PyBytes>> {
    let json_value = serialize_root_type(py, obj, &descriptor, none_value_handling)?;
    let json_bytes = serde_json::to_vec(&json_value)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    Ok(PyBytes::new_bound(py, &json_bytes).unbind())
}

fn deserialize_value(
    py: Python,
    value: &Value,
    field: &FieldDescriptor,
) -> PyResult<PyObject> {
    if value.is_null() {
        return Ok(py.None());
    }

    match field.field_type {
        FieldType::Str => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected string for field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            Ok(s.to_object(py))
        }
        FieldType::Int => {
            let i = value.as_i64().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected integer for field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            Ok(i.to_object(py))
        }
        FieldType::Float => {
            let f = value.as_f64().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected float for field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            Ok(f.to_object(py))
        }
        FieldType::Bool => {
            let b = value.as_bool().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected boolean for field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            Ok(b.to_object(py))
        }
        FieldType::List => {
            let arr = value.as_array().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected array for field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("List field missing item_schema")
            })?;
            let items: Vec<PyObject> = arr
                .iter()
                .map(|item| deserialize_value(py, item, item_schema))
                .collect::<PyResult<_>>()?;
            Ok(PyList::new_bound(py, items).to_object(py))
        }
        FieldType::Dict => {
            let obj = value.as_object().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected object for field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let value_schema = field.value_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Dict field missing value_schema")
            })?;
            let dict = PyDict::new_bound(py);
            for (k, v) in obj {
                let py_value = deserialize_value(py, v, value_schema)?;
                dict.set_item(k, py_value)?;
            }
            Ok(dict.to_object(py))
        }
        FieldType::Nested => {
            let obj = value.as_object().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Expected object for nested field '{}', got {:?}",
                    field.name, value
                ))
            })?;
            let nested_schema = field.nested_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Nested field missing nested_schema")
            })?;
            deserialize_dataclass(py, obj, &nested_schema.fields, &nested_schema.cls)
        }
    }
}

fn wrap_error_with_field(py: Python, inner: PyErr, field_name: &str) -> PyErr {
    let inner_value = inner.value_bound(py);
    if let Ok(inner_dict) = inner_value.downcast::<PyDict>() {
        let outer_dict = PyDict::new_bound(py);
        let _ = outer_dict.set_item(field_name, inner_dict);
        PyErr::new::<pyo3::exceptions::PyValueError, _>(outer_dict.to_object(py))
    } else if let Ok(args) = inner_value.getattr("args") {
        if let Ok(first_arg) = args.get_item(0) {
            if let Ok(inner_dict) = first_arg.downcast::<PyDict>() {
                let outer_dict = PyDict::new_bound(py);
                let _ = outer_dict.set_item(field_name, inner_dict);
                return PyErr::new::<pyo3::exceptions::PyValueError, _>(outer_dict.to_object(py));
            }
        }
        inner
    } else {
        inner
    }
}

fn missing_field_error(py: Python, field_name: &str) -> PyErr {
    let dict = PyDict::new_bound(py);
    let error_list = PyList::new_bound(py, vec!["Missing data for required field."]);
    let _ = dict.set_item(field_name, error_list);
    PyErr::new::<pyo3::exceptions::PyValueError, _>(dict.to_object(py))
}

fn deserialize_primitive(py: Python, value: &Value, field_type: &FieldType) -> PyResult<PyObject> {
    if value.is_null() {
        return Ok(py.None());
    }

    match field_type {
        FieldType::Str => {
            let s = value.as_str().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string")
            })?;
            Ok(s.to_object(py))
        }
        FieldType::Int => {
            let i = value.as_i64().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected integer")
            })?;
            Ok(i.to_object(py))
        }
        FieldType::Float => {
            let f = value.as_f64().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected float")
            })?;
            Ok(f.to_object(py))
        }
        FieldType::Bool => {
            let b = value.as_bool().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected boolean")
            })?;
            Ok(b.to_object(py))
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unsupported primitive type",
        )),
    }
}

fn deserialize_dataclass(
    py: Python,
    json_obj: &Map<String, Value>,
    fields: &[FieldDescriptor],
    cls: &Py<PyAny>,
) -> PyResult<PyObject> {
    let kwargs = PyDict::new_bound(py);

    for field in fields {
        let serialized_name = field.serialized_name.as_ref().unwrap_or(&field.name);

        if let Some(json_field) = json_obj.get(serialized_name) {
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
            kwargs.set_item(&field.name, py_value)?;
        } else if field.optional {
            kwargs.set_item(&field.name, py.None())?;
        } else {
            return Err(missing_field_error(py, &field.name));
        }
    }

    cls.call_bound(py, (), Some(&kwargs))
}

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

            let items: Vec<PyObject> = arr
                .iter()
                .enumerate()
                .map(|(idx, item)| {
                    deserialize_root_type(py, item, item_descriptor)
                        .map_err(|e| wrap_error_with_field(py, e, &idx.to_string()))
                })
                .collect::<PyResult<_>>()?;

            Ok(PyList::new_bound(py, items).to_object(py))
        }
        TypeKind::Dict => {
            let obj = json_value.as_object().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected JSON object")
            })?;

            let value_descriptor = descriptor.value_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict")
            })?;

            let dict = PyDict::new_bound(py);
            for (k, v) in obj {
                let val = deserialize_root_type(py, v, value_descriptor)
                    .map_err(|e| wrap_error_with_field(py, e, k))?;
                dict.set_item(k, val)?;
            }
            Ok(dict.to_object(py))
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
fn hello() -> String {
    "Hello from Rust!".to_string()
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    m.add_function(wrap_pyfunction!(dump_to_json, m)?)?;
    m.add_function(wrap_pyfunction!(load_from_json, m)?)?;
    Ok(())
}
