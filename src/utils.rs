use std::collections::HashMap;

use chrono::{DateTime, Datelike, FixedOffset, NaiveDate, NaiveDateTime, NaiveTime, Timelike};
use once_cell::sync::Lazy;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDate, PyDateTime, PyDelta, PyDeltaAccess, PyDict, PyList, PyTzInfo};
use regex::Regex;
use rust_decimal::RoundingStrategy;
use serde_json::Value;

use crate::cache::get_cached_types;

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

#[inline]
pub fn parse_iso_date(s: &str) -> Option<NaiveDate> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").ok()
}

#[inline]
pub fn parse_iso_time(s: &str) -> Option<NaiveTime> {
    NaiveTime::parse_from_str(s, "%H:%M:%S").ok()
        .or_else(|| NaiveTime::parse_from_str(s, "%H:%M:%S%.f").ok())
}

#[inline]
pub fn parse_rfc3339_datetime(s: &str) -> Option<DateTime<FixedOffset>> {
    DateTime::parse_from_rfc3339(s).ok()
}

fn python_to_chrono_format(fmt: &str) -> String {
    fmt.replace(".%f", "%.6f").replace("%f", "%6f")
}

#[inline]
pub fn parse_datetime_with_format(s: &str, fmt: &str) -> Option<DateTime<FixedOffset>> {
    let chrono_fmt = python_to_chrono_format(fmt);

    if let Ok(dt) = DateTime::parse_from_str(s, &chrono_fmt) {
        return Some(dt);
    }

    if let Ok(naive) = NaiveDateTime::parse_from_str(s, &chrono_fmt) {
        return Some(naive.and_utc().fixed_offset());
    }

    NaiveDate::parse_from_str(s, &chrono_fmt)
        .ok()
        .map(|d| d.and_hms_opt(0, 0, 0).unwrap().and_utc().fixed_offset())
}

#[inline]
#[allow(clippy::cast_possible_truncation)]
pub fn create_pydatetime_from_chrono(py: Python, dt: DateTime<FixedOffset>) -> PyResult<Py<PyAny>> {
    let offset_seconds = dt.offset().local_minus_utc();
    let cached = get_cached_types(py)?;
    let py_tz: Bound<'_, PyTzInfo> = cached.get_timezone(py, offset_seconds)?.bind(py).clone().cast_into()?;

    PyDateTime::new(
        py,
        dt.year(),
        dt.month() as u8,
        dt.day() as u8,
        dt.hour() as u8,
        dt.minute() as u8,
        dt.second() as u8,
        dt.nanosecond() / 1000,
        Some(&py_tz),
    )
    .map(|dt| dt.into_any().unbind())
}

#[inline]
#[allow(clippy::cast_possible_truncation)]
pub fn create_pydate_from_chrono(py: Python, d: NaiveDate) -> PyResult<Py<PyAny>> {
    PyDate::new(py, d.year(), d.month() as u8, d.day() as u8).map(|d| d.into_any().unbind())
}

#[inline]
#[allow(clippy::cast_possible_truncation)]
pub fn create_pytime_from_chrono(py: Python, t: NaiveTime) -> PyResult<Py<PyAny>> {
    pyo3::types::PyTime::new(py, t.hour() as u8, t.minute() as u8, t.second() as u8, t.nanosecond() / 1000, None).map(|t| t.into_any().unbind())
}

#[inline]
pub fn get_tz_offset_seconds(py: Python, tz: &Bound<'_, PyTzInfo>, reference: &Bound<'_, PyAny>) -> PyResult<i32> {
    let cached = get_cached_types(py)?;
    if tz.is(cached.utc_tz.bind(py)) {
        return Ok(0);
    }
    let offset = tz.call_method1(intern!(py, "utcoffset"), (reference,))?;
    Ok(offset.cast::<PyDelta>().map_or(0, |delta| delta.get_days() * 86400 + delta.get_seconds()))
}

#[inline]
pub fn call_validator(py: Python, validator: &Py<PyAny>, value: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let result = validator.bind(py).call1((value,))?;
    Ok((!result.is_none()).then(|| result.unbind()))
}

#[inline]
pub fn python_rounding_to_rust(rounding: Option<&Py<PyAny>>, py: Python) -> RoundingStrategy {
    rounding
        .and_then(|r| r.bind(py).extract::<&str>().ok())
        .map_or(RoundingStrategy::MidpointNearestEven, |s| match s {
            "ROUND_UP" => RoundingStrategy::AwayFromZero,
            "ROUND_DOWN" => RoundingStrategy::ToZero,
            "ROUND_CEILING" => RoundingStrategy::ToPositiveInfinity,
            "ROUND_FLOOR" => RoundingStrategy::ToNegativeInfinity,
            "ROUND_HALF_UP" => RoundingStrategy::MidpointAwayFromZero,
            "ROUND_HALF_DOWN" => RoundingStrategy::MidpointTowardZero,
            "ROUND_05UP" => panic!("ROUND_05UP is not supported in nuked implementation"),
            _ => RoundingStrategy::MidpointNearestEven,
        })
}
