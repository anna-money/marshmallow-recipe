use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};

use crate::error::{DumpError, LoadError};

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
) -> Result<Py<PyAny>, LoadError> {
    json_value_to_py(py, value)
}

pub fn load_from_py(value: &Bound<'_, PyAny>) -> Py<PyAny> {
    value.clone().unbind()
}

pub fn dump(value: &Bound<'_, PyAny>) -> Result<serde_json::Value, DumpError> {
    py_value_to_json(value)
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    validate_json_serializable(value)?;
    Ok(value.clone().unbind())
}

fn json_value_to_py(
    py: Python<'_>,
    value: &serde_json::Value,
) -> Result<Py<PyAny>, LoadError> {
    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => b
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string())),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                return i
                    .into_py_any(py)
                    .map_err(|e| LoadError::simple(&e.to_string()));
            }
            if let Some(u) = n.as_u64() {
                return u
                    .into_py_any(py)
                    .map_err(|e| LoadError::simple(&e.to_string()));
            }
            let s = n.to_string();
            if s.contains('.') || s.contains('e') || s.contains('E') {
                if let Ok(f) = s.parse::<f64>() {
                    return f
                        .into_py_any(py)
                        .map_err(|e| LoadError::simple(&e.to_string()));
                }
            }
            let int_type = crate::utils::get_int_type(py);
            int_type
                .call1((&s,))
                .map(|v| v.into_any().unbind())
                .map_err(|e| LoadError::simple(&e.to_string()))
        }
        serde_json::Value::String(s) => s
            .as_str()
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string())),
        serde_json::Value::Array(arr) => {
            let mut items = Vec::with_capacity(arr.len());
            for item in arr {
                items.push(json_value_to_py(py, item)?);
            }
            PyList::new(py, items)
                .map(|l| l.into_any().unbind())
                .map_err(|e| LoadError::simple(&e.to_string()))
        }
        serde_json::Value::Object(obj) => {
            let dict = PyDict::new(py);
            for (k, v) in obj {
                let py_val = json_value_to_py(py, v)?;
                dict.set_item(k.as_str(), py_val)
                    .map_err(|e| LoadError::simple(&e.to_string()))?;
            }
            Ok(dict.into_any().unbind())
        }
    }
}

const ANY_ERROR: &str = "Not a valid JSON-serializable value.";

fn py_value_to_json(value: &Bound<'_, PyAny>) -> Result<serde_json::Value, DumpError> {
    if value.is_none() {
        return Ok(serde_json::Value::Null);
    }
    if let Ok(b) = value.extract::<bool>() {
        return Ok(serde_json::Value::Bool(b));
    }
    if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
        if let Ok(i) = value.extract::<i64>() {
            return Ok(serde_json::Value::Number(i.into()));
        }
        if let Ok(u) = value.extract::<u64>() {
            return Ok(serde_json::Value::Number(u.into()));
        }
    }
    if value.is_instance_of::<PyFloat>() {
        if let Ok(f) = value.extract::<f64>() {
            if !f.is_nan() && !f.is_infinite() {
                return Ok(
                    serde_json::Number::from_f64(f)
                        .map_or(serde_json::Value::Null, serde_json::Value::Number),
                );
            }
        }
    }
    if let Ok(s) = value.cast::<PyString>() {
        let str_val = s.to_str().map_err(|e| DumpError::simple(&e.to_string()))?;
        return Ok(serde_json::Value::String(str_val.to_string()));
    }
    if let Ok(list) = value.cast::<PyList>() {
        let mut items = Vec::with_capacity(list.len());
        for item in list.iter() {
            items.push(py_value_to_json(&item)?);
        }
        return Ok(serde_json::Value::Array(items));
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let mut map = serde_json::Map::with_capacity(dict.len());
        for (k, v) in dict.iter() {
            let key = k
                .cast::<PyString>()
                .map_err(|_| DumpError::simple("Dict key must be a string"))?
                .to_str()
                .map_err(|e| DumpError::simple(&e.to_string()))?;
            map.insert(key.to_string(), py_value_to_json(&v)?);
        }
        return Ok(serde_json::Value::Object(map));
    }

    Err(DumpError::simple(ANY_ERROR))
}

fn validate_json_serializable(value: &Bound<'_, PyAny>) -> Result<(), DumpError> {
    if value.is_none() {
        return Ok(());
    }
    if value.extract::<bool>().is_ok() {
        return Ok(());
    }
    if value.is_instance_of::<PyInt>()
        && !value.is_instance_of::<PyBool>()
        && (value.extract::<i64>().is_ok() || value.extract::<u64>().is_ok())
    {
        return Ok(());
    }
    if value.is_instance_of::<PyFloat>() {
        if let Ok(f) = value.extract::<f64>() {
            if !f.is_nan() && !f.is_infinite() {
                return Ok(());
            }
        }
    }
    if value.is_instance_of::<PyString>() {
        return Ok(());
    }
    if let Ok(list) = value.cast::<PyList>() {
        for item in list.iter() {
            validate_json_serializable(&item)?;
        }
        return Ok(());
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        for (k, v) in dict.iter() {
            if !k.is_instance_of::<PyString>() {
                return Err(DumpError::simple(ANY_ERROR));
            }
            validate_json_serializable(&v)?;
        }
        return Ok(());
    }

    Err(DumpError::simple(ANY_ERROR))
}
