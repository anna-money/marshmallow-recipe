use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

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
            0 => Ok(PyBool::new(py, false).to_owned().into_any().unbind()),
            1 => Ok(PyBool::new(py, true).to_owned().into_any().unbind()),
            _ => Err(LoadError::simple(err_msg)),
        };
    }
    if value.is_instance_of::<PyString>() {
        let s: &str = value.extract().map_err(|_| LoadError::simple(err_msg))?;
        return match s {
            "true" => Ok(PyBool::new(py, true).to_owned().into_any().unbind()),
            "false" => Ok(PyBool::new(py, false).to_owned().into_any().unbind()),
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
