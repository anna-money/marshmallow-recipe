use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
    post_load: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let py_str = value
        .cast::<PyString>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    let result = if strip_whitespaces {
        let s = py_str
            .to_str()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(py.None());
        }
        if trimmed.len() == s.len() {
            value.clone().unbind()
        } else {
            trimmed
                .into_py_any(py)
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?
        }
    } else {
        value.clone().unbind()
    };

    if let Some(post_load_fn) = post_load {
        post_load_fn
            .call1(py, (&result,))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))
    } else {
        Ok(result)
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
