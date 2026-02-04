use chrono::NaiveTime;
use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyString, PyTime};

use crate::error::{DumpError, LoadError};
use crate::utils::display_to_py;

const TIME_ERROR: &str = "Not a valid time.";

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(TIME_ERROR);

    if let Some(s) = value.as_str() {
        return s
            .parse::<NaiveTime>()
            .map_err(|_| LoadError::simple(err_msg))
            .and_then(|t| {
                t.into_py_any(py)
                    .map_err(|e| LoadError::simple(&e.to_string()))
            });
    }

    Err(LoadError::simple(err_msg))
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(TIME_ERROR);

    if value.is_instance_of::<PyTime>() {
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>() {
        if let Ok(s) = py_str.to_str() {
            if let Ok(time) = s.parse::<NaiveTime>() {
                return time
                    .into_py_any(value.py())
                    .map_err(|e| LoadError::simple(&e.to_string()));
            }
        }
    }

    Err(LoadError::simple(err_msg))
}

pub fn dump(value: &Bound<'_, PyAny>) -> Result<serde_json::Value, DumpError> {
    let time: NaiveTime = value
        .extract()
        .map_err(|_| DumpError::simple(TIME_ERROR))?;

    Ok(serde_json::Value::String(time.to_string()))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    let time: NaiveTime = value
        .extract()
        .map_err(|_| DumpError::simple(TIME_ERROR))?;
    Ok(display_to_py::<16, _>(value.py(), &time))
}
