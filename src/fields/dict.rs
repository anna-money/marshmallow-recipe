use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};

use crate::container::FieldContainer;
use crate::error::{DumpError, LoadError};
use crate::error_convert::pyerrors_to_dump_error;
use crate::utils::{call_validator, new_presized_dict};

fn pyerrors_to_load_error(py: Python<'_>, errors: &Py<PyAny>) -> LoadError {
    fn pyany_to_load_error(py: Python<'_>, value: &Bound<'_, PyAny>) -> LoadError {
        if let Ok(s) = value.extract::<String>() {
            return LoadError::simple(py, &s);
        }
        if let Ok(list) = value.cast::<PyList>() {
            if list.is_empty() {
                return LoadError::List(list.clone().unbind());
            }
            let all_strings = list.iter().all(|item| item.extract::<String>().is_ok());
            if all_strings {
                return LoadError::List(list.clone().unbind());
            }
            if list.len() == 1
                && let Ok(item) = list.get_item(0)
            {
                return pyany_to_load_error(py, &item);
            }
            let dict = PyDict::new(py);
            for (idx, item) in list.iter().enumerate() {
                let _ = dict.set_item(idx, pyany_to_load_error(py, &item).to_py_value(py).unwrap_or_else(|_| py.None()));
            }
            return LoadError::Dict(dict.unbind());
        }
        if let Ok(dict) = value.cast::<PyDict>() {
            let result = PyDict::new(py);
            for (k, v) in dict.iter() {
                let _ = result.set_item(&k, pyany_to_load_error(py, &v).to_py_value(py).unwrap_or_else(|_| py.None()));
            }
            return LoadError::Dict(result.unbind());
        }
        LoadError::simple(py, &value.to_string())
    }

    fn maybe_wrap_nested_error(py: Python<'_>, e: LoadError) -> LoadError {
        match e {
            LoadError::Dict(d) => {
                let val = d.into_any();
                LoadError::List(PyList::new(py, [val.bind(py)]).expect("single element").unbind())
            }
            other => other,
        }
    }

    let error = pyany_to_load_error(py, errors.bind(py));
    maybe_wrap_nested_error(py, error)
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, LoadError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| LoadError::Single(invalid_error.clone_ref(py)))?;

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
                    && let Ok(Some(err_list)) =
                        call_validator(py, validator, py_val.bind(py))
                {
                    let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                    let _ = err_dict.set_item(
                        key_str,
                        pyerrors_to_load_error(py, &err_list).to_py_value(py).unwrap_or_else(|_| py.None()),
                    );
                    continue;
                }
                let _ = result.set_item(k, py_val);
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ = nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = LoadError::Dict(nested_dict.unbind());
                let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                let _ = err_dict.set_item(
                    key_str,
                    wrapped.to_py_value(py).unwrap_or_else(|_| py.None()),
                );
            }
        }
    }

    if let Some(errors) = errors {
        return Err(LoadError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, DumpError> {
    let py = value.py();

    let dict = value
        .cast::<PyDict>()
        .map_err(|_| DumpError::Single(invalid_error.clone_ref(py)))?;

    let result = new_presized_dict(py, dict.len());
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (k, v) in dict.iter() {
        let key_str = k
            .cast::<PyString>()
            .map_err(|_| DumpError::Single(intern!(py, "Dict key must be a string").clone().unbind()))?
            .to_str()
            .map_err(|e| DumpError::simple(py, &e.to_string()))?;

        if let Some(validator) = value_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &v)
        {
            let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
            let _ = err_dict.set_item(
                key_str,
                pyerrors_to_dump_error(py, &err_list).to_py_value(py).unwrap_or_else(|_| py.None()),
            );
            continue;
        }

        match value_schema.dump_to_py(&v) {
            Ok(dumped) => {
                result
                    .set_item(k, dumped)
                    .map_err(|e| DumpError::simple(py, &e.to_string()))?;
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ = nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = DumpError::Dict(nested_dict.unbind());
                let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                let _ = err_dict.set_item(
                    key_str,
                    wrapped.to_py_value(py).unwrap_or_else(|_| py.None()),
                );
            }
        }
    }

    if let Some(errors) = errors {
        return Err(DumpError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}
