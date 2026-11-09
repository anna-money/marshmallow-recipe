use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyFloat, PyInt, PyString};

use crate::error::SerializationError;
use crate::fields::int_type;
use crate::fields::range::{RangeBound, validate_range};

pub fn to_exact<'py>(value: &Bound<'py, PyAny>) -> PyResult<Option<Bound<'py, PyAny>>> {
    if value.is_exact_instance_of::<PyFloat>() {
        return Ok(None);
    }
    if let Ok(float) = value.cast::<PyFloat>() {
        return Ok(Some(PyFloat::new(value.py(), float.value()).into_any()));
    }
    int_type::to_exact(value)
}

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
    as_string: bool,
    invalid_error: &Py<PyString>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<Py<PyAny>, SerializationError> {
    if !value.is_exact_instance_of::<PyFloat>() && !value.is_exact_instance_of::<PyInt>() {
        return dump_inexact_to_py(value, as_string, invalid_error, gt, gte, lt, lte);
    }
    if let Ok(f) = value.extract::<f64>()
        && (f.is_nan() || f.is_infinite())
    {
        return Err(SerializationError::Single(
            invalid_error.clone_ref(value.py()),
        ));
    }
    validate_range(value, gt, gte, lt, lte)?;
    if as_string {
        return crate::utils::py_str(value);
    }
    Ok(value.clone().unbind())
}

#[cold]
fn dump_inexact_to_py(
    value: &Bound<'_, PyAny>,
    as_string: bool,
    invalid_error: &Py<PyString>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let exact = to_exact(value)
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?
        .ok_or_else(|| SerializationError::Single(invalid_error.clone_ref(py)))?;
    dump_to_py(&exact, as_string, invalid_error, gt, gte, lt, lte)
}
