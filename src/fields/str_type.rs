use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;
use crate::fields::length::{LengthBound, validate_length};

fn py_string_char_count(py_str: &Bound<'_, PyString>) -> usize {
    unsafe { pyo3::ffi::PyUnicode_GET_LENGTH(py_str.as_ptr()).cast_unsigned() }
}

pub fn to_exact<'py>(value: &Bound<'py, PyAny>) -> PyResult<Option<Bound<'py, PyAny>>> {
    if value.is_exact_instance_of::<PyString>() || !value.is_instance_of::<PyString>() {
        return Ok(None);
    }
    unsafe {
        Bound::from_owned_ptr_or_err(value.py(), pyo3::ffi::PyUnicode_FromObject(value.as_ptr()))
    }
    .map(Some)
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
    post_load: Option<&Py<PyAny>>,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let py_str = value
        .cast::<PyString>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    let (result, char_count) = if strip_whitespaces {
        let s = py_str
            .to_str()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(py.None());
        }
        if trimmed.len() == s.len() {
            (value.clone().unbind(), py_string_char_count(py_str))
        } else {
            let trimmed_py = PyString::new(py, trimmed);
            let count = py_string_char_count(&trimmed_py);
            (trimmed_py.unbind().into_any(), count)
        }
    } else {
        (value.clone().unbind(), py_string_char_count(py_str))
    };

    let (result, char_count) = if let Some(post_load_fn) = post_load {
        let post_result = post_load_fn
            .call1(py, (&result,))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let count = post_result
            .bind(py)
            .cast::<PyString>()
            .map_or(char_count, |s| py_string_char_count(s));
        (post_result, count)
    } else {
        (result, char_count)
    };

    validate_length(py, char_count, min_length, max_length)?;

    Ok(result)
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
) -> Result<Py<PyAny>, SerializationError> {
    if !value.is_exact_instance_of::<PyString>() {
        return dump_inexact_to_py(
            value,
            strip_whitespaces,
            allow_none,
            invalid_error,
            min_length,
            max_length,
        );
    }
    let py = value.py();
    let py_str = unsafe { value.cast_unchecked::<PyString>() };

    if strip_whitespaces {
        let s = py_str
            .to_str()
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(py.None());
        }
        if trimmed.len() == s.len() {
            validate_length(py, py_string_char_count(py_str), min_length, max_length)?;
            Ok(value.clone().unbind())
        } else {
            let trimmed_py = PyString::new(py, trimmed);
            validate_length(
                py,
                py_string_char_count(&trimmed_py),
                min_length,
                max_length,
            )?;
            Ok(trimmed_py.unbind().into_any())
        }
    } else {
        validate_length(py, py_string_char_count(py_str), min_length, max_length)?;
        Ok(value.clone().unbind())
    }
}

#[cold]
fn dump_inexact_to_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let exact = to_exact(value)
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?
        .ok_or_else(|| SerializationError::Single(invalid_error.clone_ref(py)))?;
    dump_to_py(
        &exact,
        strip_whitespaces,
        allow_none,
        invalid_error,
        min_length,
        max_length,
    )
}
