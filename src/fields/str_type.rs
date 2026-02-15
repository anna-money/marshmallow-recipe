use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::error::SerializationError;

pub struct LengthBound {
    pub value: usize,
    pub error: Py<PyString>,
}

impl Clone for LengthBound {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            value: self.value,
            error: self.error.clone_ref(py),
        })
    }
}

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

fn validate_length(
    py: Python<'_>,
    char_count: usize,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
) -> Result<(), SerializationError> {
    if let Some(bound) = min_length
        && char_count < bound.value
    {
        return Err(SerializationError::Single(bound.error.clone_ref(py)));
    }
    if let Some(bound) = max_length
        && char_count > bound.value
    {
        return Err(SerializationError::Single(bound.error.clone_ref(py)));
    }
    Ok(())
}

fn validate_regexp(
    py: Python<'_>,
    s: &str,
    regexp: Option<&RegexpBound>,
) -> Result<(), SerializationError> {
    if let Some(bound) = regexp
        && !bound.pattern.is_match(s)
    {
        return Err(SerializationError::Single(bound.error.clone_ref(py)));
    }
    Ok(())
}

pub fn load_from_py(
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
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let trimmed = s.trim();
        if allow_none && trimmed.is_empty() {
            return Ok(py.None());
        }
        validate_length(py, trimmed.chars().count(), min_length, max_length)?;
        validate_regexp(py, trimmed, regexp)?;
        if trimmed.len() == s.len() {
            Ok(value.clone().unbind())
        } else {
            Ok(PyString::new(py, trimmed).into_any().unbind())
        }
    } else {
        if min_length.is_some() || max_length.is_some() {
            let char_count = py_str
                .len()
                .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
            validate_length(py, char_count, min_length, max_length)?;
        }
        if regexp.is_some() {
            let s = py_str
                .to_str()
                .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
            validate_regexp(py, s, regexp)?;
        }
        Ok(value.clone().unbind())
    }
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
        validate_length(py, trimmed.chars().count(), min_length, max_length)?;
        validate_regexp(py, trimmed, regexp)?;
        if trimmed.len() == s.len() {
            Ok(value.clone().unbind())
        } else {
            Ok(PyString::new(py, trimmed).into_any().unbind())
        }
    } else {
        if min_length.is_some() || max_length.is_some() {
            let char_count = py_str
                .len()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            validate_length(py, char_count, min_length, max_length)?;
        }
        if regexp.is_some() {
            let s = py_str
                .to_str()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            validate_regexp(py, s, regexp)?;
        }
        Ok(value.clone().unbind())
    }
}
