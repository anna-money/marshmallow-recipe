use chrono::{DateTime, FixedOffset, NaiveDateTime};
use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDateTime, PyFloat, PyInt, PyString};

use crate::error::SerializationError;
use crate::utils::display_to_py;
use crate::utils::{parse_datetime_with_format, python_to_chrono_format};

pub const FORMAT_ISO: &str = "iso";
pub const FORMAT_TIMESTAMP: &str = "timestamp";

#[derive(Clone, Debug)]
pub enum DateTimeFormat {
    Iso,
    Timestamp,
    Strftime(String),
}

#[allow(clippy::cast_possible_truncation)]
pub fn timestamp_to_datetime(timestamp: f64) -> Option<DateTime<FixedOffset>> {
    if timestamp < 0.0 {
        return None;
    }
    let micros = (timestamp * 1_000_000.0).round() as i64;
    DateTime::from_timestamp_micros(micros).map(|dt| dt.fixed_offset())
}

pub fn parse_datetime_format(format: Option<&str>) -> DateTimeFormat {
    match format {
        None | Some(FORMAT_ISO) => DateTimeFormat::Iso,
        Some(FORMAT_TIMESTAMP) => DateTimeFormat::Timestamp,
        Some(fmt) => DateTimeFormat::Strftime(python_to_chrono_format(fmt)),
    }
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    format: &DateTimeFormat,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyDateTime>() {
        return Ok(value.clone().unbind());
    }

    match format {
        DateTimeFormat::Iso => {
            if let Ok(py_str) = value.cast::<PyString>()
                && let Ok(s) = py_str.to_str()
            {
                let dt = DateTime::<FixedOffset>::parse_from_rfc3339(s).or_else(|_| {
                    NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S")
                        .or_else(|_| NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S%.f"))
                        .map(|naive| naive.and_utc().fixed_offset())
                });
                return dt
                    .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))
                    .and_then(|dt| {
                        dt.into_py_any(py)
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))
                    });
            }
        }
        DateTimeFormat::Timestamp => {
            if value.is_instance_of::<PyFloat>()
                || (value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>())
            {
                let f: f64 = value
                    .extract()
                    .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
                return load_from_timestamp(py, f, invalid_error);
            }
        }
        DateTimeFormat::Strftime(chrono_fmt) => {
            if let Ok(py_str) = value.cast::<PyString>()
                && let Ok(s) = py_str.to_str()
                && let Some(dt) = parse_datetime_with_format(s, chrono_fmt)
            {
                return dt
                    .into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()));
            }
        }
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    format: &DateTimeFormat,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let dt = extract_datetime(value)
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    match format {
        DateTimeFormat::Iso => Ok(display_to_py::<40, _>(py, &dt.format("%+"))),
        DateTimeFormat::Timestamp => {
            let ts = datetime_to_timestamp(&dt)
                .ok_or_else(|| SerializationError::Single(invalid_error.clone_ref(py)))?;
            ts.into_py_any(py)
                .map_err(|e| SerializationError::simple(py, &e.to_string()))
        }
        DateTimeFormat::Strftime(chrono_fmt) => {
            let formatted = dt.format(chrono_fmt).to_string();
            formatted
                .into_py_any(py)
                .map_err(|e| SerializationError::simple(py, &e.to_string()))
        }
    }
}

fn extract_datetime(value: &Bound<'_, PyAny>) -> PyResult<DateTime<FixedOffset>> {
    if let Ok(dt) = value.extract::<DateTime<FixedOffset>>() {
        return Ok(dt);
    }
    let naive: NaiveDateTime = value.extract()?;
    Ok(naive.and_utc().fixed_offset())
}

#[allow(clippy::cast_precision_loss)]
fn datetime_to_timestamp(dt: &DateTime<FixedOffset>) -> Option<f64> {
    let micros = dt.timestamp_micros();
    if micros < 0 {
        return None;
    }
    Some(micros as f64 / 1_000_000.0)
}

fn load_from_timestamp(
    py: Python,
    timestamp: f64,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    timestamp_to_datetime(timestamp)
        .ok_or_else(|| SerializationError::Single(invalid_error.clone_ref(py)))
        .and_then(|dt| {
            dt.into_py_any(py)
                .map_err(|e| SerializationError::simple(py, &e.to_string()))
        })
}
