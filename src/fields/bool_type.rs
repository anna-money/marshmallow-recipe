use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::error::SerializationError;
use crate::utils::py_str;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyBool>() {
        return Ok(value.clone().unbind());
    }
    if value.is_instance_of::<PyInt>() {
        let i: i64 = value
            .extract()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        return match i {
            0 => Ok(PyBool::new(py, false).to_owned().into_any().unbind()),
            1 => Ok(PyBool::new(py, true).to_owned().into_any().unbind()),
            _ => Err(SerializationError::Single(invalid_error.clone_ref(py))),
        };
    }
    if value.is_instance_of::<PyString>() {
        let s: &str = value
            .extract()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        return match s {
            "true" | "True" | "1" => Ok(PyBool::new(py, true).to_owned().into_any().unbind()),
            "false" | "False" | "0" => Ok(PyBool::new(py, false).to_owned().into_any().unbind()),
            _ => Err(SerializationError::Single(invalid_error.clone_ref(py))),
        };
    }
    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    as_string: bool,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    if !value.is_instance_of::<PyBool>() {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }
    if as_string {
        return py_str(value);
    }
    Ok(value.clone().unbind())
}
