use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let py_str = value
        .cast::<PyString>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    if strip_whitespaces {
        let s = py_str
            .to_str()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(py.None());
        }
        if trimmed.len() == s.len() {
            return Ok(value.clone().unbind());
        }
        trimmed
            .into_py_any(py)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))
    } else {
        Ok(value.clone().unbind())
    }
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let py_str = value
        .cast::<PyString>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    if strip_whitespaces {
        let s = py_str
            .to_str()
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(py.None());
        }
        if trimmed.len() == s.len() {
            return Ok(value.clone().unbind());
        }
        trimmed
            .into_py_any(py)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))
    } else {
        Ok(value.clone().unbind())
    }
}
