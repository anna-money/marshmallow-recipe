use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

use crate::container::{DataclassRegistry, FieldContainer};
use crate::error::{SerializationError, accumulate_entry_error, pyerrors_to_serialization_error};
use crate::utils::{call_validator, get_mapping_abc};

pub fn load_from_py(
    registry: &DataclassRegistry,
    value: &Bound<'_, PyAny>,
    key_schema: Option<&FieldContainer>,
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

        let mut key_ok = true;
        let loaded_key = key_schema.and_then(|schema| match schema.load_from_py(registry, &k) {
            Ok(loaded) => Some(loaded.into_bound(py)),
            Err(ref e) => {
                accumulate_entry_error(py, &mut errors, key_str, "key", e);
                key_ok = false;
                None
            }
        });
        let target_key = loaded_key.as_ref().unwrap_or(&k);

        if v.is_none() {
            if key_ok {
                let _ = result.set_item(target_key, py.None());
            }
            return;
        }
        match value_schema.load_from_py(registry, &v) {
            Ok(py_val) => {
                if let Some(validator) = value_validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, py_val.bind(py))
                {
                    let e = pyerrors_to_serialization_error(py, &err_list);
                    accumulate_entry_error(py, &mut errors, key_str, "value", &e);
                    return;
                }
                if key_ok {
                    let _ = result.set_item(target_key, py_val);
                }
            }
            Err(ref e) => {
                accumulate_entry_error(py, &mut errors, key_str, "value", e);
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

pub fn dump_to_py(
    registry: &DataclassRegistry,
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
        let mut failed_key: Option<String> = None;
        let dumped_key = key_schema.and_then(|schema| match schema.dump_to_py(registry, &k) {
            Ok(dumped) => Some(dumped.into_bound(py)),
            Err(ref e) => {
                let raw = k.str().map(|s| s.to_string()).unwrap_or_default();
                accumulate_entry_error(py, &mut errors, raw.as_str(), "key", e);
                failed_key = Some(raw);
                None
            }
        });
        let target_key = dumped_key.as_ref().unwrap_or(&k);
        let key_str = match failed_key.as_deref() {
            Some(raw) => raw,
            None => target_key
                .cast::<PyString>()
                .map_err(|_| {
                    SerializationError::Single(
                        intern!(py, "Dict key must be a string").clone().unbind(),
                    )
                })?
                .to_str()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?,
        };

        if let Some(validator) = value_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &v)
        {
            let e = pyerrors_to_serialization_error(py, &err_list);
            accumulate_entry_error(py, &mut errors, key_str, "value", &e);
            continue;
        }

        match value_schema.dump_to_py(registry, &v) {
            Ok(dumped) => {
                if failed_key.is_none() {
                    result
                        .set_item(target_key, dumped)
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                }
            }
            Err(ref e) => {
                accumulate_entry_error(py, &mut errors, key_str, "value", e);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}
