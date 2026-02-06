use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};

use crate::container::FieldContainer;
use crate::error::{DumpError, LoadError};
use crate::error_convert::pyerrors_to_dump_error;
use crate::utils::{call_validator, new_presized_dict};

const DICT_ERROR: &str = "Not a valid dict.";

fn pyerrors_to_load_error(py: Python<'_>, errors: &Py<PyAny>) -> LoadError {
    fn pyany_to_load_error(value: &Bound<'_, PyAny>) -> LoadError {
        if let Ok(s) = value.extract::<String>() {
            return LoadError::simple(&s);
        }
        if let Ok(list) = value.cast::<PyList>() {
            if list.is_empty() {
                return LoadError::messages(vec![]);
            }
            let all_strings = list.iter().all(|item| item.extract::<String>().is_ok());
            if all_strings {
                let msgs: Vec<String> = list
                    .iter()
                    .filter_map(|v| v.extract::<String>().ok())
                    .collect();
                return LoadError::messages(msgs);
            }
            if list.len() == 1
                && let Ok(item) = list.get_item(0)
            {
                return pyany_to_load_error(&item);
            }
            let mut index_map = HashMap::with_capacity(list.len());
            for (idx, item) in list.iter().enumerate() {
                index_map.insert(idx, pyany_to_load_error(&item));
            }
            return LoadError::IndexMultiple(index_map);
        }
        if let Ok(dict) = value.cast::<PyDict>() {
            let mut map = HashMap::with_capacity(dict.len());
            for (k, v) in dict.iter() {
                let key = k.extract::<String>().unwrap_or_else(|_| k.to_string());
                map.insert(key, pyany_to_load_error(&v));
            }
            return LoadError::Multiple(map);
        }
        LoadError::simple(&value.to_string())
    }

    fn maybe_wrap_nested_error(e: LoadError) -> LoadError {
        match &e {
            LoadError::Multiple(_) | LoadError::Nested { .. } | LoadError::IndexMultiple(_) => {
                LoadError::ArrayWrapped(Box::new(e))
            }
            _ => e,
        }
    }

    let error = pyany_to_load_error(errors.bind(py));
    maybe_wrap_nested_error(error)
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

    let result = new_presized_dict(py, dict.len());
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
                if let Some(validator) = value_validator
                    && let Ok(Some(err_list)) =
                        call_validator(py, validator, py_val.bind(py))
                {
                    errors.get_or_insert_with(HashMap::new).insert(
                        key_str.to_string(),
                        pyerrors_to_load_error(py, &err_list),
                    );
                    continue;
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

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, DumpError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| DumpError::simple(DICT_ERROR))?;

    let result = new_presized_dict(py, dict.len());
    let mut errors: Option<HashMap<String, DumpError>> = None;

    for (k, v) in dict.iter() {
        let key_str = k
            .cast::<PyString>()
            .map_err(|_| DumpError::simple("Dict key must be a string"))?
            .to_str()
            .map_err(|e| DumpError::simple(&e.to_string()))?;

        if let Some(validator) = value_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &v)
        {
            errors
                .get_or_insert_with(HashMap::new)
                .insert(key_str.to_string(), pyerrors_to_dump_error(py, &err_list));
            continue;
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
