use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::container::StrLiteralData;
use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    data: &StrLiteralData,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
    {
        for allowed in &data.values {
            if allowed == s {
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    data: &StrLiteralData,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
    {
        for allowed in &data.values {
            if allowed == s {
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}
