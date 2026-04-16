use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;
use crate::fields::length::{LengthBound, validate_length};

pub struct RegexpBound {
    pub pattern: regex::Regex,
    pub error: Py<PyString>,
}

impl Clone for RegexpBound {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            pattern: self.pattern.clone(),
            error: self.error.clone_ref(py),
        })
    }
}

fn validate_regexp(
    py: Python<'_>,
    s: &str,
    regexp: Option<&RegexpBound>,
) -> Result<(), SerializationError> {
    if let Some(bound) = regexp
        && bound.pattern.find(s).is_none_or(|m| m.start() != 0)
    {
        return Err(SerializationError::Single(bound.error.clone_ref(py)));
    }
    Ok(())
}

fn py_string_char_count(py_str: &Bound<'_, PyString>) -> usize {
    unsafe { pyo3::ffi::PyUnicode_GET_LENGTH(py_str.as_ptr()).cast_unsigned() }
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
    post_load: Option<&Py<PyAny>>,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
    regexp: Option<&RegexpBound>,
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
        let (result, char_count) = if trimmed.len() == s.len() {
            (value.clone().unbind(), py_string_char_count(py_str))
        } else {
            let trimmed_py = PyString::new(py, trimmed);
            let count = py_string_char_count(&trimmed_py);
            (trimmed_py.unbind().into_any(), count)
        };
        if post_load.is_none() {
            validate_length(py, char_count, min_length, max_length)?;
            validate_regexp(py, trimmed, regexp)?;
            return Ok(result);
        }
        (result, char_count)
    } else {
        let char_count = py_string_char_count(py_str);
        if post_load.is_none() {
            validate_length(py, char_count, min_length, max_length)?;
            if regexp.is_some() {
                let s = py_str
                    .to_str()
                    .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
                validate_regexp(py, s, regexp)?;
            }
            return Ok(value.clone().unbind());
        }
        (value.clone().unbind(), char_count)
    };

    let post_load_fn = post_load.expect("post_load must be Some here");
    let result = post_load_fn
        .call1(py, (&result,))
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    let char_count = result
        .bind(py)
        .cast::<PyString>()
        .map_or(char_count, |s| py_string_char_count(s));

    validate_length(py, char_count, min_length, max_length)?;

    if regexp.is_some() {
        let s = result
            .bind(py)
            .cast::<PyString>()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?
            .to_str()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        validate_regexp(py, s, regexp)?;
    }

    Ok(result)
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    strip_whitespaces: bool,
    allow_none: bool,
    invalid_error: &Py<PyString>,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
    regexp: Option<&RegexpBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let py_str = value
        .cast::<PyString>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

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
            validate_regexp(py, trimmed, regexp)?;
            Ok(value.clone().unbind())
        } else {
            let trimmed_py = PyString::new(py, trimmed);
            validate_length(
                py,
                py_string_char_count(&trimmed_py),
                min_length,
                max_length,
            )?;
            validate_regexp(py, trimmed, regexp)?;
            Ok(trimmed_py.unbind().into_any())
        }
    } else {
        validate_length(py, py_string_char_count(py_str), min_length, max_length)?;
        if regexp.is_some() {
            let s = py_str
                .to_str()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            validate_regexp(py, s, regexp)?;
        }
        Ok(value.clone().unbind())
    }
}
