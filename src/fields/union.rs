use pyo3::intern;
use pyo3::prelude::*;

use crate::container::FieldContainer;
use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    variants: &[FieldContainer],
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let mut errors = Vec::new();
    for variant in variants {
        match variant.load_from_py(value) {
            Ok(result) => return Ok(result),
            Err(e) => errors.push(e),
        }
    }
    Err(SerializationError::collect_list(py, errors))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    variants: &[FieldContainer],
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    for variant in variants {
        if let Ok(result) = variant.dump_to_py(value) {
            return Ok(result);
        }
    }

    Err(SerializationError::Single(
        intern!(py, "Value does not match any union variant")
            .clone()
            .unbind(),
    ))
}
