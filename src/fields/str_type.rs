use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::{DumpError, LoadError};

const STR_ERROR: &str = "Not a valid string.";

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    strip_whitespaces: bool,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(STR_ERROR);

    if let Some(s) = value.as_str() {
        let result = if strip_whitespaces { s.trim() } else { s };
        return result
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string()));
    }

    Err(LoadError::simple(err_msg))
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(STR_ERROR);
    let py = value.py();

    let py_str = value
        .cast::<PyString>()
        .map_err(|_| LoadError::simple(err_msg))?;
    let s = py_str.to_str().map_err(|_| LoadError::simple(err_msg))?;
    let result = if strip_whitespaces { s.trim() } else { s };
    result
        .into_py_any(py)
        .map_err(|e| LoadError::simple(&e.to_string()))
}

pub fn dump(value: &Bound<'_, PyAny>, strip_whitespaces: bool) -> Result<serde_json::Value, DumpError> {
    let py_str = value
        .cast::<PyString>()
        .map_err(|_| DumpError::simple(STR_ERROR))?;

    let s = py_str
        .to_str()
        .map_err(|e| DumpError::simple(&e.to_string()))?;

    let result = if strip_whitespaces { s.trim() } else { s };
    Ok(serde_json::Value::String(result.to_string()))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
) -> Result<Py<PyAny>, DumpError> {
    let py_str = value
        .cast::<PyString>()
        .map_err(|_| DumpError::simple(STR_ERROR))?;

    if strip_whitespaces {
        let s = py_str
            .to_str()
            .map_err(|e| DumpError::simple(&e.to_string()))?;
        s.trim()
            .into_py_any(value.py())
            .map_err(|e| DumpError::simple(&e.to_string()))
    } else {
        Ok(value.clone().unbind())
    }
}
