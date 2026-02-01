use std::fmt::Write;

use arrayvec::ArrayString;
use chrono::{DateTime, FixedOffset, NaiveDate, NaiveDateTime, NaiveTime, SecondsFormat, TimeZone, Utc};
use pyo3::prelude::*;
use pyo3::types::{PyDateAccess, PyDateTime, PyTimeAccess, PyTzInfoAccess};

use super::helpers::{field_error, json_field_error, DATETIME_ERROR};
use crate::types::DumpContext;
use crate::utils::{get_tz_offset_seconds, parse_datetime_with_format, parse_rfc3339_datetime, python_to_chrono_format};

pub const FORMAT_ISO: &str = "iso";
pub const FORMAT_TIMESTAMP: &str = "timestamp";

pub type DateTimeIsoBuf = ArrayString<32>;
pub type DateTimeStrftimeBuf = ArrayString<128>;

pub struct DateTimeComponents {
    pub year: i32,
    pub month: u8,
    pub day: u8,
    pub hour: u8,
    pub minute: u8,
    pub second: u8,
    pub microsecond: u32,
    pub offset_seconds: Option<i32>,
}

enum StrftimeResult {
    Ok,
    InvalidDatetime,
    BufferTooSmall,
}

pub const BUFFER_ERROR_MSG: &str = "Datetime format result too long (max 128 chars).";

#[inline]
pub fn extract_components(py: Python, dt: &Bound<'_, PyDateTime>) -> PyResult<DateTimeComponents> {
    let offset_seconds = dt
        .get_tzinfo()
        .map(|tz| get_tz_offset_seconds(py, &tz, dt.as_any()))
        .transpose()?;

    Ok(DateTimeComponents {
        year: dt.get_year(),
        month: dt.get_month(),
        day: dt.get_day(),
        hour: dt.get_hour(),
        minute: dt.get_minute(),
        second: dt.get_second(),
        microsecond: dt.get_microsecond(),
        offset_seconds,
    })
}

#[inline]
fn components_to_chrono(dt: &DateTimeComponents) -> Option<DateTime<FixedOffset>> {
    let date = NaiveDate::from_ymd_opt(dt.year, dt.month.into(), dt.day.into())?;
    let time = NaiveTime::from_hms_micro_opt(
        dt.hour.into(),
        dt.minute.into(),
        dt.second.into(),
        dt.microsecond,
    )?;
    let naive = NaiveDateTime::new(date, time);
    let offset = FixedOffset::east_opt(dt.offset_seconds.unwrap_or(0))?;
    offset.from_local_datetime(&naive).single()
}

#[inline]
fn format_iso(buf: &mut DateTimeIsoBuf, dt: &DateTimeComponents) {
    if let Some(chrono_dt) = components_to_chrono(dt) {
        let formatted = chrono_dt.to_rfc3339_opts(SecondsFormat::AutoSi, false);
        buf.push_str(&formatted);
    } else {
        write!(
            buf,
            "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}",
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
        ).expect("DateTime ISO max 32 chars");
        write_tz_offset(buf, dt.offset_seconds.unwrap_or(0));
    }
}

#[inline]
fn write_tz_offset(buf: &mut DateTimeIsoBuf, offset_secs: i32) {
    let sign = if offset_secs >= 0 { '+' } else { '-' };
    let abs_secs = offset_secs.abs();
    let hours = abs_secs / 3600;
    let minutes = (abs_secs % 3600) / 60;
    write!(buf, "{sign}{hours:02}:{minutes:02}")
        .expect("DateTime ISO max 32 chars");
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
fn components_to_timestamp(dt: &DateTimeComponents) -> Option<f64> {
    let datetime = components_to_chrono(dt)?;
    let secs = datetime.timestamp();
    let micros = datetime.timestamp_subsec_micros();
    Some(secs as f64 + f64::from(micros) / 1_000_000.0)
}

#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
pub fn timestamp_to_datetime(timestamp: f64) -> Option<DateTime<FixedOffset>> {
    let secs = timestamp.trunc() as i64;
    let nanos = ((timestamp.fract().abs()) * 1_000_000_000.0).round() as u32;
    let utc_dt = Utc.timestamp_opt(secs, nanos).single()?;
    Some(utc_dt.with_timezone(&FixedOffset::east_opt(0)?))
}

#[inline]
fn format_strftime(
    buf: &mut DateTimeStrftimeBuf,
    dt: &DateTimeComponents,
    fmt: &str,
) -> StrftimeResult {
    let Some(datetime) = components_to_chrono(dt) else {
        return StrftimeResult::InvalidDatetime;
    };

    let chrono_fmt = python_to_chrono_format(fmt);
    let formatted = datetime.format(&chrono_fmt).to_string();

    if buf.try_push_str(&formatted).is_ok() {
        StrftimeResult::Ok
    } else {
        StrftimeResult::BufferTooSmall
    }
}

pub mod datetime_dumper {
    use pyo3::conversion::IntoPyObjectExt;
    use pyo3::prelude::*;
    use pyo3::types::{PyDateTime, PyString};

    use super::{
        components_to_timestamp, extract_components, field_error, format_iso, format_strftime,
        is_iso_format, is_timestamp_format, json_field_error,
        DateTimeComponents, DateTimeIsoBuf, DateTimeStrftimeBuf, DumpContext, StrftimeResult,
        BUFFER_ERROR_MSG, DATETIME_ERROR,
    };

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        value.is_instance_of::<PyDateTime>()
    }

    #[inline]
    pub fn format_to_dict(
        py: Python<'_>,
        dt: &DateTimeComponents,
        datetime_format: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        if is_iso_format(datetime_format) {
            let mut buf = DateTimeIsoBuf::new();
            format_iso(&mut buf, dt);
            return Ok(PyString::new(py, &buf).into_any().unbind());
        }

        if is_timestamp_format(datetime_format) {
            let timestamp = components_to_timestamp(dt)
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(DATETIME_ERROR))?;
            return timestamp.into_py_any(py);
        }

        let fmt = datetime_format.expect("format must be Some for strftime");
        let mut buf = DateTimeStrftimeBuf::new();
        match format_strftime(&mut buf, dt, fmt) {
            StrftimeResult::Ok => Ok(PyString::new(py, &buf).into_any().unbind()),
            StrftimeResult::InvalidDatetime => {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(DATETIME_ERROR))
            }
            StrftimeResult::BufferTooSmall => {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(BUFFER_ERROR_MSG))
            }
        }
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        datetime_format: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDateTime>() {
            return Err(field_error(ctx.py, field_name, DATETIME_ERROR));
        }
        let dt: &Bound<'_, PyDateTime> = value.cast()?;
        let components = extract_components(ctx.py, dt)?;
        format_to_dict(ctx.py, &components, datetime_format)
            .map_err(|_| field_error(ctx.py, field_name, DATETIME_ERROR))
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, '_>,
        datetime_format: Option<&str>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance_of::<PyDateTime>() {
            return Err(S::Error::custom(json_field_error(field_name, DATETIME_ERROR)));
        }
        let dt: &Bound<'_, PyDateTime> = value.cast().map_err(|e| S::Error::custom(e.to_string()))?;
        let components = extract_components(ctx.py, dt).map_err(|e| S::Error::custom(e.to_string()))?;

        if is_iso_format(datetime_format) {
            let mut buf = DateTimeIsoBuf::new();
            format_iso(&mut buf, &components);
            return serializer.serialize_str(&buf);
        }

        if is_timestamp_format(datetime_format) {
            let timestamp = components_to_timestamp(&components)
                .ok_or_else(|| S::Error::custom(json_field_error(field_name, DATETIME_ERROR)))?;
            return serializer.serialize_f64(timestamp);
        }

        let fmt = datetime_format.expect("format must be Some for strftime");
        let mut buf = DateTimeStrftimeBuf::new();
        match format_strftime(&mut buf, &components, fmt) {
            StrftimeResult::Ok => serializer.serialize_str(&buf),
            _ => Err(S::Error::custom(json_field_error(field_name, DATETIME_ERROR))),
        }
    }
}

pub mod datetime_loader {
    use pyo3::conversion::IntoPyObjectExt;
    use pyo3::prelude::*;
    use pyo3::types::{PyFloat, PyInt, PyString};
    use serde::de;

    use super::{
        field_error, is_iso_format, is_timestamp_format,
        parse_datetime_with_format, parse_rfc3339_datetime, timestamp_to_datetime, DATETIME_ERROR,
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
            return dt.into_py_any(ctx.py)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }

        let s = value.cast::<PyString>().map_err(|_| datetime_err())?;
        let s_str = s.to_str()?;

        if is_iso_format(datetime_format) {
            if let Some(dt) = parse_rfc3339_datetime(s_str) {
                return dt.into_py_any(ctx.py)
                    .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
            }
            return Err(datetime_err());
        }

        let fmt = datetime_format.expect("format must be Some for strptime");
        if let Some(dt) = parse_datetime_with_format(s_str, fmt) {
            return dt.into_py_any(ctx.py)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
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
    pub fn load_from_timestamp<E: de::Error>(
        py: Python,
        timestamp: f64,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        timestamp_to_datetime(timestamp)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|dt| dt.into_py_any(py).map_err(de::Error::custom))
    }
}
