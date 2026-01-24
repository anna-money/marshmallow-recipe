use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

pub const STR_ERROR: &str = "Not a valid string.";
pub const INT_ERROR: &str = "Not a valid integer.";
pub const FLOAT_ERROR: &str = "Not a valid number.";
pub const FLOAT_NAN_ERROR: &str = "Special numeric values (nan or infinity) are not permitted.";
pub const BOOL_ERROR: &str = "Not a valid boolean.";
pub const DECIMAL_ERROR: &str = "Not a valid decimal.";
pub const DECIMAL_NUMBER_ERROR: &str = "Not a valid number.";
pub const UUID_ERROR: &str = "Not a valid UUID.";
pub const DATE_ERROR: &str = "Not a valid date.";
pub const TIME_ERROR: &str = "Not a valid time.";
pub const DATETIME_ERROR: &str = "Not a valid datetime.";
pub const LIST_ERROR: &str = "Not a valid list.";
pub const SET_ERROR: &str = "Not a valid set.";
pub const FROZENSET_ERROR: &str = "Not a valid frozenset.";
pub const TUPLE_ERROR: &str = "Not a valid tuple.";
pub const DICT_ERROR: &str = "Not a valid dict.";
pub const NESTED_ERROR: &str = "Not a valid nested object.";
pub const ANY_ERROR: &str = "Not a valid JSON-serializable value.";
pub const UNION_ERROR: &str = "Value does not match any union variant.";

#[inline]
pub fn field_error(py: Python, field_name: &str, msg: &str) -> PyErr {
    let errors = PyList::new(py, [msg]).unwrap();
    if field_name.is_empty() {
        return PyErr::new::<pyo3::exceptions::PyValueError, _>(errors.into_any().unbind());
    }
    let dict = PyDict::new(py);
    dict.set_item(field_name, errors).unwrap();
    PyErr::new::<pyo3::exceptions::PyValueError, _>(dict.into_any().unbind())
}

#[inline]
pub fn json_field_error(field_name: &str, msg: &str) -> String {
    format!("{{\"{field_name}\": [\"{msg}\"]}}")
}

#[inline]
pub fn err_json(field_name: &str, message: &str) -> String {
    if field_name.is_empty() {
        serde_json::json!([message]).to_string()
    } else {
        let mut map = serde_json::Map::new();
        map.insert(field_name.to_string(), serde_json::json!([message]));
        serde_json::Value::Object(map).to_string()
    }
}

#[inline]
pub fn err_dict_from_list(py: Python, field_name: &str, errors: Py<PyAny>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    dict.set_item(field_name, errors).unwrap();
    dict.into()
}
