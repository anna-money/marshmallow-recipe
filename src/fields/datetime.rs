use arrayvec::ArrayString;
use chrono::{DateTime, FixedOffset, NaiveDateTime, SecondsFormat, TimeZone, Utc};
use pyo3::prelude::*;

use super::helpers::{field_error, json_field_error, DATETIME_ERROR};
use crate::types::DumpContext;
use crate::utils::{parse_datetime_with_format, parse_rfc3339_datetime, python_to_chrono_format};

fn extract_datetime(value: &Bound<'_, PyAny>) -> PyResult<DateTime<FixedOffset>> {
    if let Ok(dt) = value.extract::<DateTime<FixedOffset>>() {
        return Ok(dt);
    }
    let naive: NaiveDateTime = value.extract()?;
    Ok(naive.and_utc().fixed_offset())
}

pub const FORMAT_ISO: &str = "iso";
pub const FORMAT_TIMESTAMP: &str = "timestamp";

pub type DateTimeStrftimeBuf = ArrayString<128>;

pub const BUFFER_ERROR_MSG: &str = "Datetime format result too long (max 128 chars).";

#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
pub fn timestamp_to_datetime(timestamp: f64) -> Option<DateTime<FixedOffset>> {
    let secs = timestamp.trunc() as i64;
    let nanos = ((timestamp.fract().abs()) * 1_000_000_000.0).round() as u32;
    let utc_dt = Utc.timestamp_opt(secs, nanos).single()?;
    Some(utc_dt.with_timezone(&FixedOffset::east_opt(0)?))
}

#[inline]
fn is_iso_format(format: Option<&str>) -> bool {
    format.is_none() || format == Some(FORMAT_ISO)
}

#[inline]
fn is_timestamp_format(format: Option<&str>) -> bool {
    format == Some(FORMAT_TIMESTAMP)
}

#[inline]
#[allow(clippy::cast_precision_loss)]
fn datetime_to_timestamp(dt: &DateTime<FixedOffset>) -> f64 {
    let secs = dt.timestamp();
    let micros = dt.timestamp_subsec_micros();
    secs as f64 + f64::from(micros) / 1_000_000.0
}

#[inline]
fn format_strftime(buf: &mut DateTimeStrftimeBuf, dt: &DateTime<FixedOffset>, fmt: &str) -> bool {
    let chrono_fmt = python_to_chrono_format(fmt);
    let formatted = dt.format(&chrono_fmt).to_string();
    buf.try_push_str(&formatted).is_ok()
}

pub mod datetime_dumper {
    use pyo3::conversion::IntoPyObjectExt;
    use pyo3::prelude::*;
    use pyo3::types::{PyDateTime, PyString};

    use super::{
        datetime_to_timestamp, extract_datetime, field_error, format_strftime, is_iso_format,
        is_timestamp_format, json_field_error, DateTimeStrftimeBuf, DumpContext, SecondsFormat,
        BUFFER_ERROR_MSG, DATETIME_ERROR,
    };

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        value.is_instance_of::<PyDateTime>()
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        datetime_format: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        let chrono_dt = extract_datetime(value).map_err(|_| field_error(ctx.py, field_name, DATETIME_ERROR))?;

        if is_iso_format(datetime_format) {
            let formatted = chrono_dt.to_rfc3339_opts(SecondsFormat::AutoSi, false);
            return Ok(PyString::new(ctx.py, &formatted).into_any().unbind());
        }

        if is_timestamp_format(datetime_format) {
            return datetime_to_timestamp(&chrono_dt).into_py_any(ctx.py);
        }

        let fmt = datetime_format.expect("format must be Some for strftime");
        let mut buf = DateTimeStrftimeBuf::new();
        if format_strftime(&mut buf, &chrono_dt, fmt) {
            Ok(PyString::new(ctx.py, &buf).into_any().unbind())
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(BUFFER_ERROR_MSG))
        }
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        _ctx: &DumpContext<'_, '_>,
        datetime_format: Option<&str>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        let chrono_dt =
            extract_datetime(value).map_err(|_| S::Error::custom(json_field_error(field_name, DATETIME_ERROR)))?;

        if is_iso_format(datetime_format) {
            let formatted = chrono_dt.to_rfc3339_opts(SecondsFormat::AutoSi, false);
            return serializer.serialize_str(&formatted);
        }

        if is_timestamp_format(datetime_format) {
            return serializer.serialize_f64(datetime_to_timestamp(&chrono_dt));
        }

        let fmt = datetime_format.expect("format must be Some for strftime");
        let mut buf = DateTimeStrftimeBuf::new();
        if format_strftime(&mut buf, &chrono_dt, fmt) {
            serializer.serialize_str(&buf)
        } else {
            Err(S::Error::custom(json_field_error(field_name, BUFFER_ERROR_MSG)))
        }
    }
}

pub mod datetime_loader {
    use pyo3::conversion::IntoPyObjectExt;
    use pyo3::prelude::*;
    use pyo3::types::{PyFloat, PyInt, PyString};
    use serde::de;

    use super::{
        field_error, is_iso_format, is_timestamp_format, parse_datetime_with_format,
        parse_rfc3339_datetime, timestamp_to_datetime, DATETIME_ERROR,
    };
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
        datetime_format: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        let datetime_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(DATETIME_ERROR));

        if is_timestamp_format(datetime_format) {
            #[allow(clippy::cast_precision_loss)]
            let timestamp = if let Ok(f) = value.cast::<PyFloat>() {
                f.value()
            } else if let Ok(i) = value.cast::<PyInt>() {
                i.extract::<i64>().map_err(|_| datetime_err())? as f64
            } else {
                return Err(datetime_err());
            };
            let dt = timestamp_to_datetime(timestamp).ok_or_else(datetime_err)?;
            return dt.into_py_any(ctx.py).map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }

        let s = value.cast::<PyString>().map_err(|_| datetime_err())?;
        let s_str = s.to_str()?;

        if is_iso_format(datetime_format) {
            if let Some(dt) = parse_rfc3339_datetime(s_str) {
                return dt.into_py_any(ctx.py).map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
            }
            return Err(datetime_err());
        }

        let fmt = datetime_format.expect("format must be Some for strptime");
        if let Some(dt) = parse_datetime_with_format(s_str, fmt) {
            return dt.into_py_any(ctx.py).map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }
        Err(datetime_err())
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(
        py: Python,
        s: &str,
        format: Option<&str>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        if is_iso_format(format) {
            return parse_rfc3339_datetime(s)
                .ok_or_else(|| de::Error::custom(err_msg))
                .and_then(|dt| dt.into_py_any(py).map_err(de::Error::custom));
        }

        let fmt = format.expect("format must be Some for strptime");
        if let Some(dt) = parse_datetime_with_format(s, fmt) {
            return dt.into_py_any(py).map_err(de::Error::custom);
        }
        Err(de::Error::custom(err_msg))
    }

    #[inline]
    pub fn load_from_timestamp<E: de::Error>(py: Python, timestamp: f64, err_msg: &str) -> Result<Py<PyAny>, E> {
        timestamp_to_datetime(timestamp)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|dt| dt.into_py_any(py).map_err(de::Error::custom))
    }
}
