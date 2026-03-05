use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyString};

use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    if value.is_instance_of::<PyBytes>() {
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
    {
        return STANDARD
            .decode(s)
            .map(|bytes| PyBytes::new(py, &bytes).into_any().unbind())
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)));
    }
    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let bytes: &[u8] = value
        .extract()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
    let encoded = STANDARD.encode(bytes);
    Ok(PyString::new(py, &encoded).into_any().unbind())
}
