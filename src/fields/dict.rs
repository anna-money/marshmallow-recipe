use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

use crate::container::FieldContainer;
use crate::error::{DumpError, LoadError};
use crate::error_convert::{pyerrors_to_dump_error, pyerrors_to_load_error};
use crate::utils::call_validator;

const DICT_ERROR: &str = "Not a valid dict.";

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(DICT_ERROR);

    let obj = value
        .as_object()
        .ok_or_else(|| LoadError::simple(err_msg))?;

    let dict = PyDict::new(py);
    let mut errors: Option<HashMap<String, LoadError>> = None;

    for (key, v) in obj {
        if v.is_null() {
            let _ = dict.set_item(key.as_str(), py.None());
            continue;
        }
        match value_schema.load(py, v) {
            Ok(py_val) => {
                if let Some(validator) = value_validator {
                    if let Ok(Some(err_list)) =
                        call_validator(py, validator, py_val.bind(py))
                    {
                        errors.get_or_insert_with(HashMap::new).insert(
                            key.clone(),
                            pyerrors_to_load_error(py, &err_list),
                        );
                        continue;
                    }
                }
                let _ = dict.set_item(key.as_str(), py_val);
            }
            Err(e) => {
                let wrapped = LoadError::Nested {
                    field: "value".to_string(),
                    inner: Box::new(e),
                };
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(key.clone(), wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(LoadError::Multiple(errors));
    }

    Ok(dict.into_any().unbind())
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(DICT_ERROR);
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| LoadError::simple(err_msg))?;

    let result = PyDict::new(py);
    let mut errors: Option<HashMap<String, LoadError>> = None;

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
                if let Some(validator) = value_validator {
                    if let Ok(Some(err_list)) =
                        call_validator(py, validator, py_val.bind(py))
                    {
                        errors.get_or_insert_with(HashMap::new).insert(
                            key_str.to_string(),
                            pyerrors_to_load_error(py, &err_list),
                        );
                        continue;
                    }
                }
                let _ = result.set_item(k, py_val);
            }
            Err(e) => {
                let wrapped = LoadError::Nested {
                    field: "value".to_string(),
                    inner: Box::new(e),
                };
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(key_str.to_string(), wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(LoadError::Multiple(errors));
    }

    Ok(result.into_any().unbind())
}

pub fn dump(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
) -> Result<serde_json::Value, DumpError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| DumpError::simple(DICT_ERROR))?;

    let mut map = serde_json::Map::with_capacity(dict.len());
    let mut errors: Option<HashMap<String, DumpError>> = None;

    for (k, v) in dict.iter() {
        let key = k
            .cast::<PyString>()
            .map_err(|_| DumpError::simple("Dict key must be a string"))?
            .to_str()
            .map_err(|e| DumpError::simple(&e.to_string()))?;

        if let Some(validator) = value_validator {
            if let Ok(Some(err_list)) = call_validator(py, validator, &v) {
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(key.to_string(), pyerrors_to_dump_error(py, &err_list));
                continue;
            }
        }

        match value_schema.dump(&v) {
            Ok(dumped) => {
                map.insert(key.to_string(), dumped);
            }
            Err(e) => {
                let wrapped = DumpError::Nested {
                    field: "value".to_string(),
                    inner: Box::new(e),
                };
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(key.to_string(), wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(DumpError::Multiple(errors));
    }

    Ok(serde_json::Value::Object(map))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, DumpError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| DumpError::simple(DICT_ERROR))?;

    let result = PyDict::new(py);
    let mut errors: Option<HashMap<String, DumpError>> = None;

    for (k, v) in dict.iter() {
        let key_str = k
            .cast::<PyString>()
            .map_err(|_| DumpError::simple("Dict key must be a string"))?
            .to_str()
            .map_err(|e| DumpError::simple(&e.to_string()))?;

        if let Some(validator) = value_validator {
            if let Ok(Some(err_list)) = call_validator(py, validator, &v) {
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(key_str.to_string(), pyerrors_to_dump_error(py, &err_list));
                continue;
            }
        }

        match value_schema.dump_to_py(&v) {
            Ok(dumped) => {
                result
                    .set_item(k, dumped)
                    .map_err(|e| DumpError::simple(&e.to_string()))?;
            }
            Err(e) => {
                let wrapped = DumpError::Nested {
                    field: "value".to_string(),
                    inner: Box::new(e),
                };
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(key_str.to_string(), wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(DumpError::Multiple(errors));
    }

    Ok(result.into_any().unbind())
}
