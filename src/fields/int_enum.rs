use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    enum_values: &[(Py<PyAny>, Py<PyAny>)],
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
        for (k, member) in enum_values {
            if value.eq(k.bind(py)).unwrap_or(false) {
                return Ok(member.clone_ref(py));
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    enum_values: &[(Py<PyAny>, Py<PyAny>)],
    enum_cls: &Py<PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if !value.is_instance(enum_cls.bind(py)).unwrap_or(false) {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    if !enum_values
        .iter()
        .any(|(_, member)| value.is(member.bind(py)))
    {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let enum_value = value
        .getattr(intern!(py, "value"))
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

    Ok(enum_value.unbind())
}
