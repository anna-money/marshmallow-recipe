use chrono::{DateTime, FixedOffset, NaiveDateTime, SecondsFormat};
use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyDateTime, PyFloat, PyInt, PyString};
use serde::de;
use serde::ser::Error as SerError;

use super::helpers::{field_error, json_field_error, DATETIME_ERROR};
use crate::types::{DumpContext, LoadContext};
use crate::utils::{parse_datetime_with_format, python_to_chrono_format};

fn extract_datetime(value: &Bound<'_, PyAny>) -> PyResult<DateTime<FixedOffset>> {
    if let Ok(dt) = value.extract::<DateTime<FixedOffset>>() {
        return Ok(dt);
    }
    let naive: NaiveDateTime = value.extract()?;
    Ok(naive.and_utc().fixed_offset())
}

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

#[inline]
#[allow(clippy::cast_precision_loss)]
fn datetime_to_timestamp(dt: &DateTime<FixedOffset>) -> Option<f64> {
    let micros = dt.timestamp_micros();
    if micros < 0 {
        return None;
    }
    Some(micros as f64 / 1_000_000.0)
}

#[inline]
fn format_strftime(dt: &DateTime<FixedOffset>, chrono_fmt: &str) -> String {
    dt.format(chrono_fmt).to_string()
}

pub fn parse_datetime_format(format: Option<&str>) -> DateTimeFormat {
    match format {
        None | Some(FORMAT_ISO) => DateTimeFormat::Iso,
        Some(FORMAT_TIMESTAMP) => DateTimeFormat::Timestamp,
        Some(fmt) => DateTimeFormat::Strftime(python_to_chrono_format(fmt)),
    }
}

pub mod datetime_dumper {
    use super::{
        datetime_to_timestamp, extract_datetime, field_error, format_strftime, json_field_error,
        DateTimeFormat, DumpContext, IntoPyObjectExt, PyDateTime, PyString, SecondsFormat,
        SerError, DATETIME_ERROR,
    };
    use pyo3::prelude::*;

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        value.is_instance_of::<PyDateTime>()
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        format: &DateTimeFormat,
    ) -> PyResult<Py<PyAny>> {
        let chrono_dt = extract_datetime(value).map_err(|_| field_error(ctx.py, field_name, DATETIME_ERROR))?;

        match format {
            DateTimeFormat::Iso => {
                let formatted = chrono_dt.to_rfc3339_opts(SecondsFormat::AutoSi, false);
                Ok(PyString::new(ctx.py, &formatted).into_any().unbind())
            }
            DateTimeFormat::Timestamp => {
                let ts = datetime_to_timestamp(&chrono_dt).ok_or_else(|| field_error(ctx.py, field_name, DATETIME_ERROR))?;
                ts.into_py_any(ctx.py)
            }
            DateTimeFormat::Strftime(chrono_fmt) => {
                let formatted = format_strftime(&chrono_dt, chrono_fmt);
                Ok(PyString::new(ctx.py, &formatted).into_any().unbind())
            }
        }
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        _ctx: &DumpContext<'_, '_>,
        format: &DateTimeFormat,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        let chrono_dt =
            extract_datetime(value).map_err(|_| S::Error::custom(json_field_error(field_name, DATETIME_ERROR)))?;

        match format {
            DateTimeFormat::Iso => {
                let formatted = chrono_dt.to_rfc3339_opts(SecondsFormat::AutoSi, false);
                serializer.serialize_str(&formatted)
            }
            DateTimeFormat::Timestamp => {
                let ts = datetime_to_timestamp(&chrono_dt)
                    .ok_or_else(|| S::Error::custom(json_field_error(field_name, DATETIME_ERROR)))?;
                serializer.serialize_f64(ts)
            }
            DateTimeFormat::Strftime(chrono_fmt) => {
                let formatted = format_strftime(&chrono_dt, chrono_fmt);
                serializer.serialize_str(&formatted)
            }
        }
    }
}

pub mod datetime_loader {
    use super::{
        de, field_error, parse_datetime_with_format, timestamp_to_datetime, DateTime,
        DateTimeFormat, FixedOffset, IntoPyObjectExt, LoadContext, PyFloat, PyInt, PyString,
        DATETIME_ERROR,
    };
    use pyo3::prelude::*;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
        format: &DateTimeFormat,
    ) -> PyResult<Py<PyAny>> {
        let datetime_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(DATETIME_ERROR));

        match format {
            DateTimeFormat::Timestamp => {
                #[allow(clippy::cast_precision_loss)]
                let timestamp = if let Ok(f) = value.cast::<PyFloat>() {
                    f.value()
                } else if let Ok(i) = value.cast::<PyInt>() {
                    i.extract::<i64>().map_err(|_| datetime_err())? as f64
                } else {
                    return Err(datetime_err());
                };
                let dt = timestamp_to_datetime(timestamp).ok_or_else(datetime_err)?;
                dt.into_py_any(ctx.py).map_err(|e| field_error(ctx.py, field_name, &e.to_string()))
            }
            DateTimeFormat::Iso => {
                let s = value.cast::<PyString>().map_err(|_| datetime_err())?;
                let s_str = s.to_str()?;
                if let Ok(dt) = DateTime::<FixedOffset>::parse_from_rfc3339(s_str) {
                    return dt.into_py_any(ctx.py).map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
                }
                Err(datetime_err())
            }
            DateTimeFormat::Strftime(chrono_fmt) => {
                let s = value.cast::<PyString>().map_err(|_| datetime_err())?;
                let s_str = s.to_str()?;
                if let Some(dt) = parse_datetime_with_format(s_str, chrono_fmt) {
                    return dt.into_py_any(ctx.py).map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
                }
                Err(datetime_err())
            }
        }
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(
        py: Python,
        s: &str,
        format: &DateTimeFormat,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        match format {
            DateTimeFormat::Iso => {
                DateTime::<FixedOffset>::parse_from_rfc3339(s)
                    .map_err(|_| de::Error::custom(err_msg))
                    .and_then(|dt| dt.into_py_any(py).map_err(de::Error::custom))
            }
            DateTimeFormat::Strftime(chrono_fmt) => {
                if let Some(dt) = parse_datetime_with_format(s, chrono_fmt) {
                    return dt.into_py_any(py).map_err(de::Error::custom);
                }
                Err(de::Error::custom(err_msg))
            }
            DateTimeFormat::Timestamp => Err(de::Error::custom(err_msg)),
        }
    }

    #[inline]
    pub fn load_from_timestamp<E: de::Error>(py: Python, timestamp: f64, err_msg: &str) -> Result<Py<PyAny>, E> {
        timestamp_to_datetime(timestamp)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|dt| dt.into_py_any(py).map_err(de::Error::custom))
    }
}
