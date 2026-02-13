use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::container::StrEnumLoaderData;
use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    data: &StrEnumLoaderData,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
    {
        for (k, member) in &data.values {
            if k == s {
                return Ok(member.clone_ref(py));
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    enum_cls: &Py<PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if !value.is_instance(enum_cls.bind(py)).unwrap_or(false) {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let enum_value = value
        .getattr("value")
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

    Ok(enum_value.unbind())
}
