use std::fmt::{Display, Write};

use arrayvec::ArrayString;
use chrono::{DateTime, FixedOffset, NaiveDate, NaiveDateTime};
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyDict, PyList, PyString, PyType};
use serde_json::Value;

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

pub fn pyany_to_json_value(obj: &Bound<'_, PyAny>) -> Value {
    if let Ok(s) = obj.extract::<String>() {
        return Value::String(s);
    }
    if let Ok(list) = obj.cast::<PyList>() {
        let items: Vec<Value> = list.iter().map(|item| pyany_to_json_value(&item)).collect();
        return Value::Array(items);
    }
    if let Ok(dict) = obj.cast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (key, value) in dict.iter() {
            let key_str = key.extract::<String>().unwrap_or_else(|_| key.to_string());
            map.insert(key_str, pyany_to_json_value(&value));
        }
        return Value::Object(map);
    }
    Value::String(obj.to_string())
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

pub fn get_int_type(py: Python<'_>) -> &Bound<'_, PyType> {
    static INT_TYPE: PyOnceLock<Py<PyType>> = PyOnceLock::new();
    INT_TYPE
        .get_or_init(py, || py.get_type::<pyo3::types::PyInt>().unbind())
        .bind(py)
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
