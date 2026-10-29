use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    values: &[Py<PyAny>],
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
        for allowed in values {
            if value.eq(allowed.bind(py)).unwrap_or(false) {
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    values: &[Py<PyAny>],
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
        for allowed in values {
            if value.eq(allowed.bind(py)).unwrap_or(false) {
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}
