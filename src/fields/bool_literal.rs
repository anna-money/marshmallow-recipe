use pyo3::prelude::*;
use pyo3::types::{PyBool, PyString};

use crate::error::SerializationError;
use crate::utils::py_str;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    as_string: bool,
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

    if as_string
        && let Ok(py_string) = value.cast::<PyString>()
        && let Ok(text) = py_string.to_str()
    {
        let parsed = match text {
            "true" => Some(true),
            "false" => Some(false),
            _ => None,
        };
        if let Some(b) = parsed
            && values.contains(&b)
        {
            return Ok(PyBool::new(py, b).to_owned().into_any().unbind());
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    as_string: bool,
    values: &[bool],
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyBool>()
        && let Ok(b) = value.extract::<bool>()
    {
        for &allowed in values {
            if b == allowed {
                if as_string {
                    return py_str(value);
                }
                return Ok(value.clone().unbind());
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}
