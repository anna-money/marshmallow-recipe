use pyo3::prelude::*;
use pyo3::types::{PyBool, PyString};

use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    values: &[bool],
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyBool>()
        && let Ok(b) = value.extract::<bool>()
    {
        for &allowed in values {
            if b == allowed {
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    values: &[bool],
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyBool>()
        && let Ok(b) = value.extract::<bool>()
    {
        for &allowed in values {
            if b == allowed {
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}
