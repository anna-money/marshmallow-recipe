use std::fmt::{Display, Write};

use arrayvec::ArrayString;
use chrono::{DateTime, FixedOffset, NaiveDate, NaiveDateTime};
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyString, PyType};

pub fn display_to_py<const N: usize, T: Display>(py: Python<'_>, value: &T) -> Py<PyAny> {
    let mut buf = ArrayString::<N>::new();
    write!(&mut buf, "{value}").expect("buffer overflow");
    PyString::new(py, &buf).into_any().unbind()
}

pub fn extract_error_args(py: Python, e: &PyErr) -> Py<PyAny> {
    e.value(py)
        .getattr("args")
        .and_then(|args| args.get_item(0))
        .map_or_else(|_| e.value(py).clone().into_any().unbind(), |v| v.clone().unbind())
}

pub fn python_to_chrono_format(fmt: &str) -> String {
    fmt.replace(".%f", "%.6f").replace("%f", "%6f")
}

#[inline]
pub fn parse_datetime_with_format(s: &str, chrono_fmt: &str) -> Option<DateTime<FixedOffset>> {
    if let Ok(dt) = DateTime::parse_from_str(s, chrono_fmt) {
        return Some(dt);
    }

    if let Ok(naive) = NaiveDateTime::parse_from_str(s, chrono_fmt) {
        return Some(naive.and_utc().fixed_offset());
    }

    NaiveDate::parse_from_str(s, chrono_fmt)
        .ok()
        .and_then(|d| d.and_hms_opt(0, 0, 0))
        .map(|dt| dt.and_utc().fixed_offset())
}

#[inline]
pub fn call_validator(py: Python, validator: &Py<PyAny>, value: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let result = validator.bind(py).call1((value,))?;
    Ok((!result.is_none()).then(|| result.unbind()))
}

pub fn get_object_cls(py: Python<'_>) -> PyResult<&Bound<'_, PyType>> {
    static OBJECT_CLS: PyOnceLock<Py<PyType>> = PyOnceLock::new();
    OBJECT_CLS.import(py, "builtins", "object")
}

pub fn get_int_cls(py: Python<'_>) -> PyResult<&Bound<'_, PyType>> {
    static INT_CLS: PyOnceLock<Py<PyType>> = PyOnceLock::new();
    INT_CLS.import(py, "builtins", "int")
}
pub fn get_missing_sentinel(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
    static MISSING_SENTINEL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
    MISSING_SENTINEL
        .get_or_try_init(py, || {
            let mod_ = py.import("marshmallow_recipe.missing")?;
            mod_.getattr("MISSING").map(Bound::unbind)
        })
        .map(|v| v.bind(py))
}
