use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::error::DumpError;

pub fn pyerrors_to_dump_error(py: Python<'_>, errors: &Py<PyAny>) -> DumpError {
    let error = pyany_to_dump_error(errors.bind(py));
    maybe_wrap_dump_nested_error(error)
}

fn pyany_to_dump_error(value: &Bound<'_, PyAny>) -> DumpError {
    if let Ok(s) = value.extract::<String>() {
        return DumpError::simple(&s);
    }
    if let Ok(list) = value.cast::<PyList>() {
        if list.is_empty() {
            return DumpError::messages(vec![]);
        }
        let all_strings = list.iter().all(|item| item.extract::<String>().is_ok());
        if all_strings {
            let msgs: Vec<String> = list
                .iter()
                .filter_map(|v| v.extract::<String>().ok())
                .collect();
            return DumpError::messages(msgs);
        }
        if list.len() == 1
            && let Ok(item) = list.get_item(0)
        {
            return pyany_to_dump_error(&item);
        }
        let mut errors = HashMap::with_capacity(list.len());
        for (idx, item) in list.iter().enumerate() {
            errors.insert(idx, pyany_to_dump_error(&item));
        }
        return DumpError::IndexMultiple(errors);
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let mut map = HashMap::with_capacity(dict.len());
        for (k, v) in dict.iter() {
            let key = k.extract::<String>().unwrap_or_else(|_| k.to_string());
            map.insert(key, pyany_to_dump_error(&v));
        }
        return DumpError::Multiple(map);
    }
    DumpError::simple(&value.to_string())
}

fn maybe_wrap_dump_nested_error(e: DumpError) -> DumpError {
    match &e {
        DumpError::Multiple(_) | DumpError::IndexMultiple(_) | DumpError::Nested { .. } => {
            DumpError::ArrayWrapped(Box::new(e))
        }
        _ => e,
    }
}
