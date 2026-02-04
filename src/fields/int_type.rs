use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::error::{DumpError, LoadError};

const INT_ERROR: &str = "Not a valid integer.";

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(INT_ERROR);

    if let Some(i) = value.as_i64() {
        return i
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(u) = value.as_u64() {
        return u
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(n) = value.as_number() {
        let s = n.to_string();
        let int_type = crate::utils::get_int_type(py);
        return int_type
            .call1((&s,))
            .map(|v| v.into_any().unbind())
            .map_err(|_| LoadError::simple(err_msg));
    }
    if let Some(s) = value.as_str() {
        if let Ok(i) = s.parse::<i64>() {
            return i
                .into_py_any(py)
                .map_err(|e| LoadError::simple(&e.to_string()));
        }
    }

    Err(LoadError::simple(err_msg))
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(INT_ERROR);
    let py = value.py();

    if value.is_instance_of::<PyBool>() {
        return Err(LoadError::simple(err_msg));
    }
    if value.is_instance_of::<PyInt>() {
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>() {
        if let Ok(s) = py_str.to_str() {
            if let Ok(i) = s.parse::<i64>() {
                return i
                    .into_py_any(py)
                    .map_err(|e| LoadError::simple(&e.to_string()));
            }
        }
    }

    Err(LoadError::simple(err_msg))
}

pub fn dump(value: &Bound<'_, PyAny>) -> Result<serde_json::Value, DumpError> {
    if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
        return Err(DumpError::simple(INT_ERROR));
    }

    if let Ok(i) = value.extract::<i64>() {
        return Ok(serde_json::Value::Number(i.into()));
    }
    if let Ok(u) = value.extract::<u64>() {
        return Ok(serde_json::Value::Number(u.into()));
    }

    let s: String = value
        .str()
        .map_err(|e| DumpError::simple(&e.to_string()))?
        .extract()
        .map_err(|e: PyErr| DumpError::simple(&e.to_string()))?;

    Ok(serde_json::Value::Number(
        serde_json::Number::from_string_unchecked(s),
    ))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
        return Err(DumpError::simple(INT_ERROR));
    }
    Ok(value.clone().unbind())
}
