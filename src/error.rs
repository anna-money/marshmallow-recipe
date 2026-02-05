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

    pub fn to_py_value(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match self {
            Self::Simple(msg) => {
                let list = PyList::new(py, [msg.as_str()])?;
                Ok(list.into_any().unbind())
            }
            Self::Messages(msgs) => {
                let list = PyList::new(py, msgs.iter().map(String::as_str))?;
                Ok(list.into_any().unbind())
            }
            Self::Nested { field, inner } => {
                let inner_val = inner.to_py_value(py)?;
                if field.is_empty() {
                    Ok(inner_val)
                } else {
                    let dict = PyDict::new(py);
                    dict.set_item(field.as_str(), inner_val)?;
                    Ok(dict.into_any().unbind())
                }
            }
            Self::Multiple(map) => {
                let dict = PyDict::new(py);
                for (k, v) in map {
                    dict.set_item(k.as_str(), v.to_py_value(py)?)?;
                }
                Ok(dict.into_any().unbind())
            }
            Self::IndexMultiple(map) => {
                let dict = PyDict::new(py);
                for (idx, v) in map {
                    let key = (*idx).into_py_any(py)?;
                    dict.set_item(key, v.to_py_value(py)?)?;
                }
                Ok(dict.into_any().unbind())
            }
            Self::ArrayWrapped(inner) => {
                let inner_val = inner.to_py_value(py)?;
                let list = PyList::new(py, [inner_val])?;
                Ok(list.into_any().unbind())
            }
            Self::Array(items) => {
                let mut py_items = Vec::with_capacity(items.len());
                for item in items {
                    py_items.push(item.to_py_value(py)?);
                }
                let list = PyList::new(py, py_items)?;
                Ok(list.into_any().unbind())
            }
        }
    }

    pub fn to_py_err(&self, py: Python<'_>) -> PyErr {
        if let Ok(py_val) = self.to_py_value(py) {
            return PyErr::new::<pyo3::exceptions::PyValueError, _>(py_val);
        }
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("{self:?}"))
    }
}

impl std::fmt::Debug for SerializationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Simple(msg) => write!(f, "Simple({msg})"),
            Self::Messages(msgs) => write!(f, "Messages({msgs:?})"),
            Self::Nested { field, inner } => write!(f, "Nested({field}: {inner:?})"),
            Self::Multiple(map) => write!(f, "Multiple({map:?})"),
            Self::IndexMultiple(map) => write!(f, "IndexMultiple({map:?})"),
            Self::ArrayWrapped(inner) => write!(f, "ArrayWrapped({inner:?})"),
            Self::Array(items) => write!(f, "Array({items:?})"),
        }
    }
}
