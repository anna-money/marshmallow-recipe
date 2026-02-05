use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::error::{DumpError, LoadError};
use crate::utils::get_int_cls;

const INT_ERROR: &str = "Not a valid integer.";

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
    if let Ok(py_str) = value.cast::<PyString>()
    {
        if let Ok(s) = py_str.to_str() && let Ok(i) = s.parse::<i128>() {
            return i
                .into_py_any(py)
                .map_err(|e| LoadError::simple(&e.to_string()));
        }

        let int_cls = get_int_cls(py).map_err(|e| LoadError::simple(&e.to_string()))?;
        return int_cls.call1((py_str,))
            .map(Bound::unbind)
            .map_err(|_| LoadError::simple(err_msg))
    }

    Err(LoadError::simple(err_msg))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
        return Err(DumpError::simple(INT_ERROR));
    }
    Ok(value.clone().unbind())
}
