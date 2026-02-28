use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

use crate::container::FieldContainer;
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
use crate::utils::call_validator;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    key_schema: Option<&FieldContainer>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    let result = PyDict::new(py);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (k, v) in dict.iter() {
        let key_str = k.str().map(|s| s.to_string()).unwrap_or_default();

        let loaded_key = if let Some(ks) = key_schema {
            match ks.load_from_py(&k) {
                Ok(lk) => lk,
                Err(e) => {
                    accumulate_error(py, &mut errors, &key_str, &e);
                    continue;
                }
            }
        } else {
            k.unbind()
        };

        if v.is_none() {
            let _ = result.set_item(&loaded_key, py.None());
            continue;
        }
        match value_schema.load_from_py(&v) {
            Ok(py_val) => {
                if let Some(validator) = value_validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, py_val.bind(py))
                {
                    let e = pyerrors_to_serialization_error(py, &err_list);
                    accumulate_error(py, &mut errors, &key_str, &e);
                    continue;
                }
                let _ = result.set_item(&loaded_key, py_val);
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ =
                    nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = SerializationError::Dict(nested_dict.unbind());
                accumulate_error(py, &mut errors, &key_str, &wrapped);
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
    key_schema: Option<&FieldContainer>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    let result = PyDict::new(py);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (k, v) in dict.iter() {
        let (dumped_key, key_str) = if let Some(ks) = key_schema {
            match ks.dump_to_py(&k) {
                Ok(dk) => {
                    let s = dk.bind(py).str().map(|s| s.to_string()).unwrap_or_default();
                    (dk, s)
                }
                Err(e) => {
                    let s = k.str().map(|s| s.to_string()).unwrap_or_default();
                    accumulate_error(py, &mut errors, &s, &e);
                    continue;
                }
            }
        } else {
            let s = k
                .cast::<PyString>()
                .map_err(|_| {
                    SerializationError::Single(
                        intern!(py, "Dict key must be a string").clone().unbind(),
                    )
                })?
                .to_str()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?
                .to_string();
            (k.unbind(), s)
        };

        if let Some(validator) = value_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &v)
        {
            let e = pyerrors_to_serialization_error(py, &err_list);
            accumulate_error(py, &mut errors, &key_str, &e);
            continue;
        }

        match value_schema.dump_to_py(&v) {
            Ok(dumped) => {
                result
                    .set_item(&dumped_key, dumped)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ =
                    nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = SerializationError::Dict(nested_dict.unbind());
                accumulate_error(py, &mut errors, &key_str, &wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}
