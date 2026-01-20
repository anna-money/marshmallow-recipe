use std::fmt::Write;

use pyo3::prelude::*;
use pyo3::types::{PyDateTime, PyDateAccess, PyString, PyTimeAccess, PyTzInfoAccess};
use serde_json::Value;

use super::helpers::{field_error, json_field_error, DATETIME_ERROR};
use crate::types::SerializeContext;
use crate::utils::{create_pydatetime_from_speedate, get_tz_offset_seconds, parse_datetime_with_format, parse_rfc3339_datetime};

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
fn format_iso(buf: &mut arrayvec::ArrayString<32>, dt: &DateTimeComponents) {
    if dt.microsecond > 0 {
        write!(
            buf,
            "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}",
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond
        ).unwrap();
    } else {
        write!(
            buf,
            "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}",
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
        ).unwrap();
    }
    write_tz_offset(buf, dt.offset_seconds.unwrap_or(0));
}

#[inline]
fn write_tz_offset(buf: &mut arrayvec::ArrayString<32>, offset_secs: i32) {
    let sign = if offset_secs >= 0 { '+' } else { '-' };
    let abs_secs = offset_secs.abs();
    let hours = abs_secs / 3600;
    let minutes = (abs_secs % 3600) / 60;
    write!(buf, "{sign}{hours:02}:{minutes:02}").unwrap();
}

#[inline]
fn format_strftime(
    buf: &mut arrayvec::ArrayString<128>,
    dt: &DateTimeComponents,
    fmt: &str,
) -> StrftimeResult {
    let Ok(year_u16) = u16::try_from(dt.year) else {
        return StrftimeResult::InvalidDatetime;
    };

    let speedate_dt = speedate::DateTime {
        date: speedate::Date { year: year_u16, month: dt.month, day: dt.day },
        time: speedate::Time {
            hour: dt.hour,
            minute: dt.minute,
            second: dt.second,
            microsecond: dt.microsecond,
            tz_offset: None
        },
    };

    let Ok(s) = time_format::strftime_utc(fmt, speedate_dt.timestamp()) else {
        return StrftimeResult::InvalidDatetime;
    };

    let final_str = if fmt.contains("%z") || fmt.contains("%Z") {
        apply_offset_to_formatted(&s, dt.offset_seconds.unwrap_or(0))
    } else {
        s
    };

    if buf.try_push_str(&final_str).is_ok() {
        StrftimeResult::Ok
    } else {
        StrftimeResult::BufferTooSmall
    }
}

fn apply_offset_to_formatted(s: &str, offset_secs: i32) -> String {
    let sign = if offset_secs >= 0 { '+' } else { '-' };
    let abs_secs = offset_secs.abs();
    let hours = abs_secs / 3600;
    let minutes = (abs_secs % 3600) / 60;
    let offset_str = format!("{sign}{hours:02}{minutes:02}");
    let offset_colon_str = format!("{sign}{hours:02}:{minutes:02}");

    s.replace("+0000", &offset_str)
        .replace("+00:00", &offset_colon_str)
        .replace("UTC", &offset_str)
}

pub mod datetime_serializer {
    use super::*;

    #[inline]
    #[allow(clippy::option_if_let_else)]
    pub fn serialize_to_dict(
        py: Python<'_>,
        dt: &DateTimeComponents,
        datetime_format: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        if let Some(fmt) = datetime_format {
            let mut buf = arrayvec::ArrayString::<128>::new();
            match format_strftime(&mut buf, dt, fmt) {
                StrftimeResult::Ok => Ok(PyString::new(py, &buf).into_any().unbind()),
                StrftimeResult::InvalidDatetime => {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(DATETIME_ERROR))
                }
                StrftimeResult::BufferTooSmall => {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(BUFFER_ERROR_MSG))
                }
            }
        } else {
            let mut buf = arrayvec::ArrayString::<32>::new();
            format_iso(&mut buf, dt);
            Ok(PyString::new(py, &buf).into_any().unbind())
        }
    }

    #[inline]
    #[allow(clippy::option_if_let_else)]
    pub fn serialize_to_json(
        dt: &DateTimeComponents,
        datetime_format: Option<&str>,
    ) -> Result<Value, ()> {
        if let Some(fmt) = datetime_format {
            let mut buf = arrayvec::ArrayString::<128>::new();
            match format_strftime(&mut buf, dt, fmt) {
                StrftimeResult::Ok => Ok(Value::String(buf.to_string())),
                StrftimeResult::InvalidDatetime | StrftimeResult::BufferTooSmall => Err(()),
            }
        } else {
            let mut buf = arrayvec::ArrayString::<32>::new();
            format_iso(&mut buf, dt);
            Ok(Value::String(buf.to_string()))
        }
    }

    #[inline]
    pub fn serialize_value_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        datetime_format: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDateTime>() {
            return Err(field_error(ctx.py, field_name, DATETIME_ERROR));
        }
        let dt: &Bound<'_, PyDateTime> = value.cast()?;
        let components = extract_components(ctx.py, dt)?;
        serialize_to_dict(ctx.py, &components, datetime_format)
            .map_err(|_| field_error(ctx.py, field_name, DATETIME_ERROR))
    }

    #[inline]
    pub fn serialize_value_to_json<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        datetime_format: Option<&str>,
    ) -> Result<Value, String> {
        if !value.is_instance_of::<PyDateTime>() {
            return Err(json_field_error(field_name, DATETIME_ERROR));
        }
        let dt: &Bound<'_, PyDateTime> = value.cast().map_err(|e| e.to_string())?;
        let offset_seconds = dt
            .get_tzinfo()
            .map(|tz| get_tz_offset_seconds(ctx.py, &tz, dt.as_any()))
            .transpose()
            .map_err(|e| e.to_string())?;

        let components = DateTimeComponents {
            year: dt.get_year(),
            month: dt.get_month(),
            day: dt.get_day(),
            hour: dt.get_hour(),
            minute: dt.get_minute(),
            second: dt.get_second(),
            microsecond: dt.get_microsecond(),
            offset_seconds,
        };

        serialize_to_json(&components, datetime_format)
            .map_err(|()| json_field_error(field_name, DATETIME_ERROR))
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, '_>,
        datetime_format: Option<&str>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance_of::<PyDateTime>() {
            return Err(S::Error::custom(json_field_error(field_name, DATETIME_ERROR)));
        }
        let dt: &Bound<'_, PyDateTime> = value.cast().map_err(|e| S::Error::custom(e.to_string()))?;
        let offset_seconds = dt
            .get_tzinfo()
            .map(|tz| get_tz_offset_seconds(ctx.py, &tz, dt.as_any()))
            .transpose()
            .map_err(|e| S::Error::custom(e.to_string()))?;

        let components = DateTimeComponents {
            year: dt.get_year(),
            month: dt.get_month(),
            day: dt.get_day(),
            hour: dt.get_hour(),
            minute: dt.get_minute(),
            second: dt.get_second(),
            microsecond: dt.get_microsecond(),
            offset_seconds,
        };

        if let Some(fmt) = datetime_format {
            let mut buf = arrayvec::ArrayString::<128>::new();
            match format_strftime(&mut buf, &components, fmt) {
                StrftimeResult::Ok => serializer.serialize_str(&buf),
                _ => Err(S::Error::custom(json_field_error(field_name, DATETIME_ERROR))),
            }
        } else {
            let mut buf = arrayvec::ArrayString::<32>::new();
            format_iso(&mut buf, &components);
            serializer.serialize_str(&buf)
        }
    }
}

pub mod datetime_deserializer {
    use super::*;
    use crate::types::LoadContext;
    use serde::de;

    #[inline]
    pub fn deserialize_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
        datetime_format: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        let datetime_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(DATETIME_ERROR));
        let s = value.cast::<PyString>().map_err(|_| datetime_err())?;
        let s_str = s.to_str()?;

        if let Some(fmt) = datetime_format {
            if let Some(dt) = parse_datetime_with_format(s_str, fmt) {
                return create_pydatetime_from_speedate(ctx.py, &dt)
                    .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
            }
            return Err(datetime_err());
        }

        if let Some(dt) = parse_rfc3339_datetime(s_str) {
            return create_pydatetime_from_speedate(ctx.py, &dt)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }
        Err(datetime_err())
    }

    #[inline]
    pub fn deserialize_from_str<E: de::Error>(
        py: Python,
        s: &str,
        format: Option<&str>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        if let Some(fmt) = format {
            if let Some(dt) = parse_datetime_with_format(s, fmt) {
                return create_pydatetime_from_speedate(py, &dt).map_err(de::Error::custom);
            }
            return Err(de::Error::custom(err_msg));
        }
        parse_rfc3339_datetime(s)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|dt| create_pydatetime_from_speedate(py, &dt).map_err(de::Error::custom))
    }
}
