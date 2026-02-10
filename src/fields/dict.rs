use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

use crate::container::FieldContainer;
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
use crate::utils::{call_validator, new_presized_dict};

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    let result = new_presized_dict(py, dict.len());
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (k, v) in dict.iter() {
        let key_str = k
            .cast::<PyString>()
            .ok()
            .and_then(|s| s.to_str().ok())
            .unwrap_or("");

        if v.is_none() {
            let _ = result.set_item(k, py.None());
            continue;
        }
        match value_schema.load_from_py(&v) {
            Ok(py_val) => {
                if let Some(validator) = value_validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, py_val.bind(py))
                {
                    let e = pyerrors_to_serialization_error(py, &err_list);
                    accumulate_error(py, &mut errors, key_str, &e);
                    continue;
                }
                let _ = result.set_item(k, py_val);
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ =
                    nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = SerializationError::Dict(nested_dict.unbind());
                accumulate_error(py, &mut errors, key_str, &wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    let result = new_presized_dict(py, dict.len());
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (k, v) in dict.iter() {
        let key_str = k
            .cast::<PyString>()
            .map_err(|_| {
                SerializationError::Single(
                    intern!(py, "Dict key must be a string").clone().unbind(),
                )
            })?
            .to_str()
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        if let Some(validator) = value_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &v)
        {
            let e = pyerrors_to_serialization_error(py, &err_list);
            accumulate_error(py, &mut errors, key_str, &e);
            continue;
        }

        match value_schema.dump_to_py(&v) {
            Ok(dumped) => {
                result
                    .set_item(k, dumped)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ =
                    nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = SerializationError::Dict(nested_dict.unbind());
                accumulate_error(py, &mut errors, key_str, &wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}
