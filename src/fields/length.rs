use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;

pub struct LengthBound {
    pub value: usize,
    pub error: Py<PyString>,
}

impl Clone for LengthBound {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            value: self.value,
            error: self.error.clone_ref(py),
        })
    }
}

pub fn validate_length(
    py: Python<'_>,
    len: usize,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
) -> Result<(), SerializationError> {
    if let Some(bound) = min_length
        && len < bound.value
    {
        return Err(SerializationError::Single(bound.error.clone_ref(py)));
    }
    if let Some(bound) = max_length
        && len > bound.value
    {
        return Err(SerializationError::Single(bound.error.clone_ref(py)));
    }
    Ok(())
}
