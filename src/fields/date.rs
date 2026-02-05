use chrono::NaiveDate;
use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyDate, PyString};

use crate::error::{DumpError, LoadError};
use crate::utils::display_to_py;

const DATE_ERROR: &str = "Not a valid date.";

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(DATE_ERROR);

    if value.is_instance_of::<PyDate>() {
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
        && let Ok(date) = s.parse::<NaiveDate>()
    {
        return date
            .into_py_any(value.py())
            .map_err(|e| LoadError::simple(&e.to_string()));
    }

    Err(LoadError::simple(err_msg))
}

pub fn dump_to_py(value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, DumpError> {
    let date: NaiveDate = value
        .extract()
        .map_err(|_| DumpError::simple(DATE_ERROR))?;
    Ok(display_to_py::<16, _>(value.py(), &date))
}
