use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyFloat, PyInt, PyString};

use crate::error::{DumpError, LoadError};

const FLOAT_ERROR: &str = "Not a valid number.";
const FLOAT_NAN_ERROR: &str = "Special numeric values (nan or infinity) are not permitted.";

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(FLOAT_ERROR);
    let nan_err = invalid_error.unwrap_or(FLOAT_NAN_ERROR);

    if let Some(i) = value.as_i64() {
        return i
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(u) = value.as_u64() {
        return u
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(f) = value.as_f64() {
        if f.is_nan() || f.is_infinite() {
            return Err(LoadError::simple(nan_err));
        }
        return f
            .into_py_any(py)
            .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(s) = value.as_str() {
        if let Ok(f) = s.parse::<f64>() {
            if f.is_nan() || f.is_infinite() {
                return Err(LoadError::simple(nan_err));
            }
            return f
                .into_py_any(py)
                .map_err(|e| LoadError::simple(&e.to_string()));
        }
    }

    Err(LoadError::simple(err_msg))
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(FLOAT_ERROR);
    let nan_err = invalid_error.unwrap_or(FLOAT_NAN_ERROR);
    let py = value.py();

    if value.is_instance_of::<PyBool>() {
        return Err(LoadError::simple(err_msg));
    }
    if value.is_instance_of::<PyInt>() {
        return Ok(value.clone().unbind());
    }
    if value.is_instance_of::<PyFloat>() {
        let f: f64 = value.extract().map_err(|_| LoadError::simple(err_msg))?;
        if f.is_nan() || f.is_infinite() {
            return Err(LoadError::simple(nan_err));
        }
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>() {
        if let Ok(s) = py_str.to_str() {
            if let Ok(f) = s.parse::<f64>() {
                if f.is_nan() || f.is_infinite() {
                    return Err(LoadError::simple(nan_err));
                }
                return f
                    .into_py_any(py)
                    .map_err(|e| LoadError::simple(&e.to_string()));
            }
        }
    }

    Err(LoadError::simple(err_msg))
}

pub fn dump(value: &Bound<'_, PyAny>) -> Result<serde_json::Value, DumpError> {
    if value.is_instance_of::<PyBool>() {
        return Err(DumpError::simple(FLOAT_ERROR));
    }

    if value.is_instance_of::<PyInt>() {
        if let Ok(i) = value.extract::<i64>() {
            return Ok(serde_json::Value::Number(i.into()));
        }
        if let Ok(u) = value.extract::<u64>() {
            return Ok(serde_json::Value::Number(u.into()));
        }
        let s: String = value
            .str()
            .map_err(|e| DumpError::simple(&e.to_string()))?
            .extract()
            .map_err(|e: PyErr| DumpError::simple(&e.to_string()))?;
        return Ok(serde_json::Value::Number(
            serde_json::Number::from_string_unchecked(s),
        ));
    }

    let f: f64 = value
        .extract()
        .map_err(|_| DumpError::simple(FLOAT_ERROR))?;

    if f.is_nan() || f.is_infinite() {
        return Err(DumpError::simple(FLOAT_NAN_ERROR));
    }

    Ok(serde_json::Number::from_f64(f).map_or(serde_json::Value::Null, serde_json::Value::Number))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    if value.is_instance_of::<PyBool>() {
        return Err(DumpError::simple(FLOAT_ERROR));
    }
    if value.is_instance_of::<PyInt>() || value.is_instance_of::<PyFloat>() {
        if let Ok(f) = value.extract::<f64>() {
            if f.is_nan() || f.is_infinite() {
                return Err(DumpError::simple(FLOAT_NAN_ERROR));
            }
        }
        return Ok(value.clone().unbind());
    }
    Err(DumpError::simple(FLOAT_ERROR))
}
