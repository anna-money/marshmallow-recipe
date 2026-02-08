use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::error::DumpError;

pub fn pyerrors_to_dump_error(py: Python<'_>, errors: &Py<PyAny>) -> DumpError {
    let error = pyany_to_dump_error(py, errors.bind(py));
    maybe_wrap_dump_nested_error(py, error)
}

fn pyany_to_dump_error(py: Python<'_>, value: &Bound<'_, PyAny>) -> DumpError {
    if let Ok(s) = value.extract::<String>() {
        return DumpError::simple(py, &s);
    }
    if let Ok(list) = value.cast::<PyList>() {
        if list.is_empty() {
            return DumpError::List(list.clone().unbind());
        }
        let all_strings = list.iter().all(|item| item.extract::<String>().is_ok());
        if all_strings {
            return DumpError::List(list.clone().unbind());
        }
        if list.len() == 1
            && let Ok(item) = list.get_item(0)
        {
            return pyany_to_dump_error(py, &item);
        }
        let dict = PyDict::new(py);
        for (idx, item) in list.iter().enumerate() {
            let _ = dict.set_item(idx, pyany_to_dump_error(py, &item).to_py_value(py).unwrap_or_else(|_| py.None()));
        }
        return DumpError::Dict(dict.unbind());
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let result = PyDict::new(py);
        for (k, v) in dict.iter() {
            let _ = result.set_item(&k, pyany_to_dump_error(py, &v).to_py_value(py).unwrap_or_else(|_| py.None()));
        }
        return DumpError::Dict(result.unbind());
    }
    DumpError::simple(py, &value.to_string())
}

fn maybe_wrap_dump_nested_error(py: Python<'_>, e: DumpError) -> DumpError {
    match e {
        DumpError::Dict(d) => {
            let val = d.into_any();
            DumpError::List(PyList::new(py, [val.bind(py)]).expect("single element").unbind())
        }
        other => other,
    }
}
