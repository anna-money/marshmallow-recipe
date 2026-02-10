use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;
use crate::utils::display_to_py;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if let Ok(uuid) = value.extract::<::uuid::Uuid>() {
        return uuid
            .into_pyobject(py)
            .map(|b| b.into_any().unbind())
            .map_err(|e| SerializationError::simple(py, &e.to_string()));
    }
    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
    {
        return ::uuid::Uuid::parse_str(s)
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))
            .and_then(|u| {
                u.into_pyobject(py)
                    .map(|b| b.into_any().unbind())
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            });
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let uuid: ::uuid::Uuid = value
        .extract()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
    Ok(display_to_py::<36, _>(py, &uuid))
}
