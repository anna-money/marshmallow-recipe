use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt};

use crate::error::{DumpError, LoadError};

const BOOL_ERROR: &str = "Not a valid boolean.";

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(BOOL_ERROR);
    let py = value.py();

    if value.is_instance_of::<PyBool>() {
        return Ok(value.clone().unbind());
    }
    if value.is_instance_of::<PyInt>() {
        let i: i64 = value.extract().map_err(|_| LoadError::simple(err_msg))?;
        return match i {
            0 => false
                .into_py_any(py)
                .map_err(|e| LoadError::simple(&e.to_string())),
            1 => true
                .into_py_any(py)
                .map_err(|e| LoadError::simple(&e.to_string())),
            _ => Err(LoadError::simple(err_msg)),
        };
    }

    Err(LoadError::simple(err_msg))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    if !value.is_instance_of::<PyBool>() {
        return Err(DumpError::simple(BOOL_ERROR));
    }
    Ok(value.clone().unbind())
}
