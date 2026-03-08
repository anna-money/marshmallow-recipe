use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyFloat, PyInt, PyString};

use crate::error::SerializationError;
use crate::fields::decimal::{RangeBound, validate_range};

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyBool>() {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }
    if value.is_instance_of::<PyInt>() {
        validate_range(value, gt, gte, lt, lte)?;
        return Ok(value.clone().unbind());
    }
    if value.is_instance_of::<PyFloat>() {
        let f: f64 = value
            .extract()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        if f.is_nan() || f.is_infinite() {
            return Err(SerializationError::Single(invalid_error.clone_ref(py)));
        }
        validate_range(value, gt, gte, lt, lte)?;
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
        && let Ok(f) = s.parse::<f64>()
    {
        if f.is_nan() || f.is_infinite() {
            return Err(SerializationError::Single(invalid_error.clone_ref(py)));
        }
        let result = f
            .into_py_any(py)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        validate_range(result.bind(py), gt, gte, lt, lte)?;
        return Ok(result);
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    if value.is_instance_of::<PyBool>() {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }
    if value.is_instance_of::<PyInt>() || value.is_instance_of::<PyFloat>() {
        if let Ok(f) = value.extract::<f64>()
            && (f.is_nan() || f.is_infinite())
        {
            return Err(SerializationError::Single(invalid_error.clone_ref(py)));
        }
        validate_range(value, gt, gte, lt, lte)?;
        return Ok(value.clone().unbind());
    }
    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}
