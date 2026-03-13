use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;

pub struct RangeBound {
    pub value: Py<PyAny>,
    pub error: Py<PyString>,
}

impl Clone for RangeBound {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            value: self.value.clone_ref(py),
            error: self.error.clone_ref(py),
        })
    }
}

pub fn validate_range(
    value: &Bound<'_, PyAny>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<(), SerializationError> {
    let py = value.py();
    if let Some(bound) = gt {
        let ok = value
            .gt(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    if let Some(bound) = gte {
        let ok = value
            .ge(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    if let Some(bound) = lt {
        let ok = value
            .lt(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    if let Some(bound) = lte {
        let ok = value
            .le(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    Ok(())
}
