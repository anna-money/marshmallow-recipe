use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

use crate::container::{DataclassRegistry, FieldContainer};
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
use crate::utils::{call_validator, get_mapping_abc};

pub fn load_from_py(
    registry: &DataclassRegistry,
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let result = PyDict::new(py);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    let mut handle = |k: Bound<'_, PyAny>, v: Bound<'_, PyAny>| {
        let key_str = k
            .cast::<PyString>()
            .ok()
            .and_then(|s| s.to_str().ok())
            .unwrap_or("");

        if v.is_none() {
            let _ = result.set_item(&k, py.None());
            return;
        }
        match value_schema.load_from_py(registry, &v) {
            Ok(py_val) => {
                if let Some(validator) = value_validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, py_val.bind(py))
                {
                    let e = pyerrors_to_serialization_error(py, &err_list);
                    accumulate_error(py, &mut errors, key_str, &e);
                    return;
                }
                let _ = result.set_item(&k, py_val);
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ =
                    nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = SerializationError::Dict(nested_dict.unbind());
                accumulate_error(py, &mut errors, key_str, &wrapped);
            }
        }
    };

    if let Ok(dict) = value.cast::<PyDict>() {
        for (k, v) in dict.iter() {
            handle(k, v);
        }
    } else {
        let mapping_abc = get_mapping_abc(py)
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        if !value.is_instance(mapping_abc).unwrap_or(false) {
            return Err(SerializationError::Single(invalid_error.clone_ref(py)));
        }
        let iter = value
            .try_iter()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        for k_result in iter {
            let k =
                k_result.map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
            let v = value
                .get_item(&k)
                .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
            handle(k, v);
        }
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}
