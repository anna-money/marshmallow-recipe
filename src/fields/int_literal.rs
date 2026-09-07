use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::error::SerializationError;
use crate::utils::py_str;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    as_string: bool,
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

    if as_string && value.is_instance_of::<PyString>() {
        for allowed in values {
            if let Ok(text) = py_str(allowed.bind(py))
                && value.eq(text.bind(py)).unwrap_or(false)
            {
                return Ok(allowed.clone_ref(py));
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    as_string: bool,
    values: &[Py<PyAny>],
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
        for allowed in values {
            if value.eq(allowed.bind(py)).unwrap_or(false) {
                if as_string {
                    return py_str(value);
                }
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}
