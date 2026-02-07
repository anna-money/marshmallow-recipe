use pyo3::prelude::*;

use crate::container::FieldContainer;
use crate::error::{DumpError, LoadError};

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    variants: &[FieldContainer],
) -> Result<Py<PyAny>, LoadError> {
    let mut errors = Vec::new();
    for variant in variants {
        match variant.load_from_py(value) {
            Ok(result) => return Ok(result),
            Err(e) => errors.push(e),
        }
    }
    Err(LoadError::Array(errors))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    variants: &[FieldContainer],
) -> Result<Py<PyAny>, DumpError> {
    for variant in variants {
        if let Ok(result) = variant.dump_to_py(value) {
            return Ok(result);
        }
    }

    Err(DumpError::simple("Value does not match any union variant"))
}
