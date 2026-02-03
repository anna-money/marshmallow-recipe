use std::collections::HashMap;

use chrono::{DateTime, FixedOffset, NaiveDate, NaiveDateTime};
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use regex::Regex;
use serde_json::Value;

static SERDE_LOCATION_SUFFIX: Lazy<Regex> =
    Lazy::new(|| Regex::new(r" at line \d+ column \d+").unwrap());

pub fn strip_serde_locations(s: &str) -> String {
    SERDE_LOCATION_SUFFIX.replace_all(s, "").into_owned()
}

pub fn try_wrap_err_json(field_name: &str, inner: &str) -> Option<String> {
    let cleaned = strip_serde_locations(inner);
    let inner_value: Value = serde_json::from_str(&cleaned).ok()?;

    if field_name.is_empty() {
        return Some(inner_value.to_string());
    }

    let mut map = serde_json::Map::new();
    map.insert(field_name.to_string(), inner_value);
    Some(Value::Object(map).to_string())
}

pub fn format_item_errors_dict(py: Python, errors: &HashMap<usize, Py<PyAny>>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    for (idx, err_list) in errors {
        dict.set_item(*idx, err_list).unwrap();
    }
    dict.into()
}

pub fn wrap_err_dict(py: Python, key: &str, inner: Py<PyAny>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    dict.set_item(key, inner).unwrap();
    dict.into()
}

pub fn wrap_err_dict_idx(py: Python, idx: usize, inner: Py<PyAny>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    dict.set_item(idx, inner).unwrap();
    dict.into()
}

pub fn extract_error_value(py: Python, e: &PyErr) -> Py<PyAny> {
    let value = extract_error_args(py, e);

    if let Ok(dict) = value.bind(py).cast::<PyDict>() {
        if dict.len() == 1 {
            if let Some(inner) = dict.get_item("").ok().flatten() {
                return inner.unbind();
            }
        }
    }
    value
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
        .map(|d| d.and_hms_opt(0, 0, 0).unwrap().and_utc().fixed_offset())
}

#[inline]
pub fn call_validator(py: Python, validator: &Py<PyAny>, value: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let result = validator.bind(py).call1((value,))?;
    Ok((!result.is_none()).then(|| result.unbind()))
}
