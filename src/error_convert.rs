use std::collections::HashMap;

use pyo3::prelude::*;

use crate::error::{DumpError, LoadError};

pub fn pyerrors_to_load_error(py: Python<'_>, errors: &Py<PyAny>) -> LoadError {
    let json_value = crate::utils::pyany_to_json_value(errors.bind(py));
    let error = json_value_to_load_error(&json_value);
    maybe_wrap_load_nested_error(error)
}

pub fn json_value_to_load_error(value: &serde_json::Value) -> LoadError {
    match value {
        serde_json::Value::Array(arr) => {
            if arr.is_empty() {
                return LoadError::messages(vec![]);
            }
            if arr.iter().all(serde_json::Value::is_string) {
                let msgs: Vec<String> = arr
                    .iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect();
                LoadError::messages(msgs)
            } else if arr.len() == 1 {
                json_value_to_load_error(&arr[0])
            } else {
                let mut index_map = HashMap::with_capacity(arr.len());
                for (idx, v) in arr.iter().enumerate() {
                    index_map.insert(idx, json_value_to_load_error(v));
                }
                LoadError::IndexMultiple(index_map)
            }
        }
        serde_json::Value::Object(obj) => {
            let mut map = HashMap::with_capacity(obj.len());
            for (k, v) in obj {
                map.insert(k.clone(), json_value_to_load_error(v));
            }
            LoadError::Multiple(map)
        }
        serde_json::Value::String(s) => LoadError::simple(s),
        _ => LoadError::simple(&value.to_string()),
    }
}

pub fn maybe_wrap_load_nested_error(e: LoadError) -> LoadError {
    match &e {
        LoadError::Multiple(_) | LoadError::Nested { .. } | LoadError::IndexMultiple(_) => {
            LoadError::ArrayWrapped(Box::new(e))
        }
        _ => e,
    }
}

pub fn pyerrors_to_dump_error(py: Python<'_>, errors: &Py<PyAny>) -> DumpError {
    let json_value = crate::utils::pyany_to_json_value(errors.bind(py));
    let error = json_value_to_dump_error(&json_value);
    maybe_wrap_dump_nested_error(error)
}

pub fn json_value_to_dump_error(value: &serde_json::Value) -> DumpError {
    match value {
        serde_json::Value::Array(arr) => {
            if arr.is_empty() {
                return DumpError::messages(vec![]);
            }
            if arr.iter().all(serde_json::Value::is_string) {
                let msgs: Vec<String> = arr
                    .iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect();
                DumpError::messages(msgs)
            } else if arr.len() == 1 {
                json_value_to_dump_error(&arr[0])
            } else {
                let mut errors = HashMap::with_capacity(arr.len());
                for (idx, v) in arr.iter().enumerate() {
                    errors.insert(idx, json_value_to_dump_error(v));
                }
                DumpError::IndexMultiple(errors)
            }
        }
        serde_json::Value::Object(obj) => {
            let mut map = HashMap::with_capacity(obj.len());
            for (k, v) in obj {
                map.insert(k.clone(), json_value_to_dump_error(v));
            }
            DumpError::Multiple(map)
        }
        serde_json::Value::String(s) => DumpError::simple(s),
        _ => DumpError::simple(&value.to_string()),
    }
}

pub fn maybe_wrap_dump_nested_error(e: DumpError) -> DumpError {
    match &e {
        DumpError::Multiple(_) | DumpError::IndexMultiple(_) | DumpError::Nested { .. } => {
            DumpError::ArrayWrapped(Box::new(e))
        }
        _ => e,
    }
}
