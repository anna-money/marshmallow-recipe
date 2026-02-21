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
    } else if let Ok(s) = value.cast::<PyString>()
        && let Ok(int_val) = s.to_str().unwrap_or("").parse::<i64>()
    {
        let int_obj = int_val.into_pyobject(py).unwrap().into_any();
        for (k, member) in &data.values {
            if int_obj.eq(k.bind(py)).unwrap_or(false) {
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
