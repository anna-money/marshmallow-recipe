use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::{DumpError, LoadError};
use crate::utils::display_to_py;

const UUID_ERROR: &str = "Not a valid UUID.";

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(UUID_ERROR);

    if let Some(s) = value.as_str() {
        return ::uuid::Uuid::parse_str(s)
            .map_err(|_| LoadError::simple(err_msg))
            .and_then(|u| {
                u.into_pyobject(py)
                    .map(|b| b.into_any().unbind())
                    .map_err(|e| LoadError::simple(&e.to_string()))
            });
    }

    Err(LoadError::simple(err_msg))
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(UUID_ERROR);
    let py = value.py();

    if let Ok(uuid) = value.extract::<::uuid::Uuid>() {
        return uuid
            .into_pyobject(py)
            .map(|b| b.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Ok(py_str) = value.cast::<PyString>() {
        if let Ok(s) = py_str.to_str() {
            return ::uuid::Uuid::parse_str(s)
                .map_err(|_| LoadError::simple(err_msg))
                .and_then(|u| {
                    u.into_pyobject(py)
                        .map(|b| b.into_any().unbind())
                        .map_err(|e| LoadError::simple(&e.to_string()))
                });
        }
    }

    Err(LoadError::simple(err_msg))
}

pub fn dump(value: &Bound<'_, PyAny>) -> Result<serde_json::Value, DumpError> {
    let uuid: ::uuid::Uuid = value
        .extract()
        .map_err(|_| DumpError::simple(UUID_ERROR))?;

    Ok(serde_json::Value::String(uuid.to_string()))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    let uuid: ::uuid::Uuid = value
        .extract()
        .map_err(|_| DumpError::simple(UUID_ERROR))?;
    Ok(display_to_py::<36, _>(value.py(), &uuid))
}
