use std::collections::HashMap;
use std::sync::RwLock;

use once_cell::sync::Lazy;
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

static FORMAT_CACHE: Lazy<RwLock<HashMap<String, &'static str>>> = Lazy::new(|| RwLock::new(HashMap::new()));

fn get_static_format(fmt: &str) -> &'static str {
    if let Some(cached) = FORMAT_CACHE.read().unwrap().get(fmt) {
        return cached;
    }
    FORMAT_CACHE.write().unwrap().entry(fmt.to_string()).or_insert_with(|| {
        Box::leak(fmt.to_string().into_boxed_str())
    })
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
pub fn parse_iso_date(s: &str) -> Option<speedate::Date> {
    speedate::Date::parse_str(s).ok()
}

#[inline]
pub fn parse_iso_time(s: &str) -> Option<speedate::Time> {
    speedate::Time::parse_str(s).ok()
}

#[inline]
pub fn parse_rfc3339_datetime(s: &str) -> Option<speedate::DateTime> {
    speedate::DateTime::parse_str(s).ok()
}

fn extract_microseconds_for_format(s: &str, fmt: &str) -> Option<(String, String, u32)> {
    let f_pos = fmt.find("%f")?;
    let prefix_before_f = &fmt[..f_pos];
    let suffix_after_f = &fmt[f_pos + 2..];

    let literal_before = prefix_before_f.chars().last()?;
    let mut s_pos = 0;
    for c in prefix_before_f.chars() {
        if c == '%' {
            continue;
        }
        if let Some(idx) = s[s_pos..].find(c) {
            s_pos += idx + 1;
        }
    }
    s_pos = s_pos.saturating_sub(1);
    let dot_pos = s[s_pos..].find(literal_before).map(|i| s_pos + i)?;

    let micro_start = dot_pos + 1;
    if micro_start + 6 > s.len() {
        return None;
    }
    let micro_str = &s[micro_start..micro_start + 6];
    if !micro_str.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    let microseconds = micro_str.parse::<u32>().ok()?;

    let modified_s = format!("{}{}", &s[..dot_pos], &s[micro_start + 6..]);
    let modified_fmt = format!("{}{}", &fmt[..f_pos - 1], suffix_after_f);

    Some((modified_s, modified_fmt, microseconds))
}

#[inline]
pub fn parse_datetime_with_format(s: &str, fmt: &str) -> Option<speedate::DateTime> {
    let (parse_s, parse_fmt, extracted_microseconds) = if fmt.contains("%f") {
        let (modified_s, modified_fmt, micros) = extract_microseconds_for_format(s, fmt)?;
        (modified_s, modified_fmt, Some(micros))
    } else {
        (s.to_string(), fmt.to_string(), None)
    };

    let fmt_static = get_static_format(&parse_fmt);
    let raw = strptime::Parser::new(fmt_static).parse(&parse_s).ok()?;
    let date = raw.date().ok()?;

    let speedate_date = speedate::Date {
        year: u16::try_from(date.year()).ok()?,
        month: date.month(),
        day: date.day(),
    };

    let speedate_time = raw.time().map_or_else(
        |_| speedate::Time { hour: 0, minute: 0, second: 0, microsecond: extracted_microseconds.unwrap_or(0), tz_offset: Some(0) },
        |t| speedate::Time {
            hour: t.hour(),
            minute: t.minute(),
            second: t.second(),
            microsecond: extracted_microseconds.unwrap_or_else(|| (t.nanosecond() / 1000).try_into().unwrap_or(0)),
            tz_offset: t.utc_offset(),
        },
    );

    Some(speedate::DateTime { date: speedate_date, time: speedate_time })
}

#[inline]
pub fn create_pydatetime_from_speedate(py: Python, dt: &speedate::DateTime) -> PyResult<Py<PyAny>> {
    let offset_seconds = dt.time.tz_offset.unwrap_or(0);
    let cached = get_cached_types(py)?;

    let py_tz: Bound<'_, PyTzInfo> = if offset_seconds == 0 {
        cached.utc_tz.bind(py).clone().cast_into()?
    } else {
        let py_delta = PyDelta::new(py, 0, offset_seconds, 0, true)?;
        cached.timezone_cls.bind(py).call1((py_delta,))?.cast_into()?
    };

    PyDateTime::new(
        py,
        i32::from(dt.date.year),
        dt.date.month,
        dt.date.day,
        dt.time.hour,
        dt.time.minute,
        dt.time.second,
        dt.time.microsecond,
        Some(&py_tz),
    )
    .map(|dt| dt.into_any().unbind())
}

#[inline]
pub fn create_pydate_from_speedate(py: Python, d: &speedate::Date) -> PyResult<Py<PyAny>> {
    PyDate::new(py, i32::from(d.year), d.month, d.day).map(|d| d.into_any().unbind())
}

#[inline]
pub fn create_pytime_from_speedate(py: Python, t: &speedate::Time) -> PyResult<Py<PyAny>> {
    pyo3::types::PyTime::new(py, t.hour, t.minute, t.second, t.microsecond, None).map(|t| t.into_any().unbind())
}

#[inline]
pub fn get_tz_offset_seconds(py: Python, tz: &Bound<'_, PyTzInfo>, reference: &Bound<'_, PyAny>) -> PyResult<i32> {
    let cached = get_cached_types(py)?;
    if tz.is(cached.utc_tz.bind(py)) {
        return Ok(0);
    }
    let offset = tz.call_method1(cached.str_utcoffset.bind(py), (reference,))?;
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
