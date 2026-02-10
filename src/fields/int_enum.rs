use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::container::IntEnumLoaderData;
use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    data: &IntEnumLoaderData,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
        for (k, member) in &data.values {
            if value.eq(k.bind(py)).unwrap_or(false) {
                return Ok(member.clone_ref(py));
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}
