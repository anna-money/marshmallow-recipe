use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

use crate::error::SerializationError;
use crate::utils::get_int_cls;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyBool>() {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }
    if value.is_instance_of::<PyInt>() {
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>() {
        if let Ok(s) = py_str.to_str()
            && let Ok(i) = s.parse::<i128>()
        {
            return i
                .into_py_any(py)
                .map_err(|e| SerializationError::simple(py, &e.to_string()));
        }

        let int_cls =
            get_int_cls(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        return int_cls
            .call1((py_str,))
            .map(Bound::unbind)
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)));
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }
    Ok(value.clone().unbind())
}
