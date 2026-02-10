use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};
use smallvec::SmallVec;

use crate::error::SerializationError;

pub fn load_from_py(value: &Bound<'_, PyAny>) -> Py<PyAny> {
    value.clone().unbind()
}

const ANY_ERROR: &str = "Not a valid JSON-serializable value.";

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, SerializationError> {
    validate_json_serializable(value)?;
    Ok(value.clone().unbind())
}

fn validate_json_serializable(value: &Bound<'_, PyAny>) -> Result<(), SerializationError> {
    let py = value.py();
    let mut stack: SmallVec<[Bound<'_, PyAny>; 32]> = SmallVec::new();
    stack.push(value.clone());

    while let Some(current) = stack.pop() {
        if current.is_none()
            || current.is_instance_of::<PyBool>()
            || current.is_instance_of::<PyInt>()
            || current.is_instance_of::<PyString>()
        {
            continue;
        }
        if current.is_instance_of::<PyFloat>()
            && let Ok(f) = current.extract::<f64>()
            && !f.is_nan()
            && !f.is_infinite()
        {
            continue;
        }
        if current.is_instance_of::<PyFloat>() {
            return Err(SerializationError::Single(
                intern!(py, ANY_ERROR).clone().unbind(),
            ));
        }
        if let Ok(list) = current.cast::<PyList>() {
            stack.extend(list.iter());
            continue;
        }
        if let Ok(dict) = current.cast::<PyDict>() {
            for (k, v) in dict.iter() {
                if !k.is_instance_of::<PyString>() {
                    return Err(SerializationError::Single(
                        intern!(py, ANY_ERROR).clone().unbind(),
                    ));
                }
                stack.push(v);
            }
            continue;
        }
        return Err(SerializationError::Single(
            intern!(py, ANY_ERROR).clone().unbind(),
        ));
    }

    Ok(())
}
