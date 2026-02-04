use std::collections::HashMap;

use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

pub enum SerializationError {
    Simple(String),
    Messages(Vec<String>),
    Nested { field: String, inner: Box<Self> },
    Multiple(HashMap<String, Self>),
    IndexMultiple(HashMap<usize, Self>),
    ArrayWrapped(Box<Self>),
    Array(Vec<Self>),
}

pub type DumpError = SerializationError;
pub type LoadError = SerializationError;

impl SerializationError {
    pub fn simple(msg: &str) -> Self {
        Self::Simple(msg.to_string())
    }

    #[allow(clippy::missing_const_for_fn)]
    pub fn messages(msgs: Vec<String>) -> Self {
        Self::Messages(msgs)
    }

    pub fn to_json(&self) -> serde_json::Value {
        match self {
            Self::Simple(msg) => serde_json::json!([msg]),
            Self::Messages(msgs) => serde_json::json!(msgs),
            Self::Nested { field, inner } => {
                let inner_json = inner.to_json();
                if field.is_empty() {
                    inner_json
                } else {
                    serde_json::json!({ field: inner_json })
                }
            }
            Self::Multiple(map) => {
                let mut result = serde_json::Map::new();
                for (k, v) in map {
                    result.insert(k.clone(), v.to_json());
                }
                serde_json::Value::Object(result)
            }
            Self::IndexMultiple(map) => {
                let mut result = serde_json::Map::new();
                for (idx, v) in map {
                    result.insert(idx.to_string(), v.to_json());
                }
                serde_json::Value::Object(result)
            }
            Self::ArrayWrapped(inner) => {
                serde_json::json!([inner.to_json()])
            }
            Self::Array(items) => {
                serde_json::json!(items.iter().map(Self::to_json).collect::<Vec<_>>())
            }
        }
    }

    pub fn to_py_err(&self, py: Python<'_>) -> PyErr {
        let json_value = self.to_json();
        if let Ok(py_val) = json_to_py_error(py, &json_value) {
            return PyErr::new::<pyo3::exceptions::PyValueError, _>(py_val);
        }
        PyErr::new::<pyo3::exceptions::PyValueError, _>(json_value.to_string())
    }
}

pub fn json_to_py_error(py: Python<'_>, value: &serde_json::Value) -> PyResult<Py<PyAny>> {
    match value {
        serde_json::Value::Object(obj) => {
            let dict = PyDict::new(py);
            for (k, v) in obj {
                let key: Py<PyAny> = if !k.is_empty() && k.chars().all(|c| c.is_ascii_digit()) {
                    k.parse::<i64>()
                        .map_err(|_| {
                            pyo3::exceptions::PyValueError::new_err(format!(
                                "Index {k} is too large"
                            ))
                        })?
                        .into_pyobject(py)?
                        .into_any()
                        .unbind()
                } else {
                    k.as_str().into_pyobject(py)?.into_any().unbind()
                };
                dict.set_item(key, json_to_py_error(py, v)?)?;
            }
            Ok(dict.into_any().unbind())
        }
        serde_json::Value::Array(arr) => {
            let list = PyList::empty(py);
            for item in arr {
                list.append(json_to_py_error(py, item)?)?;
            }
            Ok(list.into_any().unbind())
        }
        serde_json::Value::String(s) => Ok(s.as_str().into_pyobject(py)?.into_any().unbind()),
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => Ok((*b).into_py_any(py)?),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_pyobject(py)?.into_any().unbind())
            } else if let Some(u) = n.as_u64() {
                Ok(u.into_pyobject(py)?.into_any().unbind())
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_pyobject(py)?.into_any().unbind())
            } else {
                Ok(py.None())
            }
        }
    }
}
