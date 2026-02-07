use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::{DumpError, LoadError};

const STR_ERROR: &str = "Not a valid string.";

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(STR_ERROR);
    let py = value.py();

    let py_str = value
        .cast::<PyString>()
        .map_err(|_| LoadError::simple(err_msg))?;

    if strip_whitespaces {
        let s = py_str.to_str().map_err(|_| LoadError::simple(err_msg))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(py.None());
        }
        if trimmed.len() == s.len() {
            return Ok(value.clone().unbind());
        }
        trimmed
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string()))
    } else {
        Ok(value.clone().unbind())
    }
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
) -> Result<Py<PyAny>, DumpError> {
    let py_str = value
        .cast::<PyString>()
        .map_err(|_| DumpError::simple(STR_ERROR))?;

    if strip_whitespaces {
        let s = py_str
            .to_str()
            .map_err(|e| DumpError::simple(&e.to_string()))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(value.py().None());
        }
        if trimmed.len() == s.len() {
            return Ok(value.clone().unbind());
        }
        trimmed
            .into_py_any(value.py())
            .map_err(|e| DumpError::simple(&e.to_string()))
    } else {
        Ok(value.clone().unbind())
    }
}
