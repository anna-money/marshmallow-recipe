use chrono::NaiveTime;
use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyString, PyTime};

use crate::error::{DumpError, LoadError};
use crate::utils::display_to_py;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, LoadError> {
    let py = value.py();

    if value.is_instance_of::<PyTime>() {
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
        && let Ok(time) = s.parse::<NaiveTime>()
    {
        return time
            .into_py_any(py)
            .map_err(|e| LoadError::simple(py, &e.to_string()));
    }

    Err(LoadError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>, invalid_error: &Py<PyString>) -> Result<Py<PyAny>, DumpError> {
    let py = value.py();
    let time: NaiveTime = value
        .extract()
        .map_err(|_| DumpError::Single(invalid_error.clone_ref(py)))?;
    Ok(display_to_py::<16, _>(py, &time))
}
