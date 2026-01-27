use std::fmt::Write;

use arrayvec::ArrayString;
use chrono::{DateTime, FixedOffset, NaiveDate, NaiveDateTime, NaiveTime};
use pyo3::prelude::*;
use pyo3::types::{PyDateAccess, PyDateTime, PyTimeAccess, PyTzInfoAccess};

use super::helpers::{field_error, json_field_error, DATETIME_ERROR};
use crate::types::DumpContext;
use crate::utils::{create_pydatetime_from_chrono, get_tz_offset_seconds, parse_datetime_with_format, parse_rfc3339_datetime};

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
fn format_iso(buf: &mut DateTimeIsoBuf, dt: &DateTimeComponents) {
    if dt.microsecond > 0 {
        write!(
            buf,
            "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}",
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond
        ).expect("DateTime ISO max 32 chars: YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM");
    } else {
        write!(
            buf,
            "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}",
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
        ).expect("DateTime ISO max 32 chars: YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM");
    }
    write_tz_offset(buf, dt.offset_seconds.unwrap_or(0));
}

#[inline]
fn write_tz_offset(buf: &mut DateTimeIsoBuf, offset_secs: i32) {
    let sign = if offset_secs >= 0 { '+' } else { '-' };
    let abs_secs = offset_secs.abs();
    let hours = abs_secs / 3600;
    let minutes = (abs_secs % 3600) / 60;
    write!(buf, "{sign}{hours:02}:{minutes:02}")
        .expect("DateTime ISO max 32 chars: YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM");
}

fn python_to_chrono_format(fmt: &str) -> String {
    fmt.replace(".%f", "%.6f").replace("%f", "%6f")
}

#[inline]
fn format_strftime(
    buf: &mut DateTimeStrftimeBuf,
    dt: &DateTimeComponents,
    fmt: &str,
) -> StrftimeResult {
    let Some(date) = NaiveDate::from_ymd_opt(dt.year, dt.month.into(), dt.day.into()) else {
        return StrftimeResult::InvalidDatetime;
    };
    let Some(time) = NaiveTime::from_hms_micro_opt(
        dt.hour.into(), dt.minute.into(), dt.second.into(), dt.microsecond
    ) else {
        return StrftimeResult::InvalidDatetime;
    };
    let naive = NaiveDateTime::new(date, time);

    let Some(offset) = FixedOffset::east_opt(dt.offset_seconds.unwrap_or(0)) else {
        return StrftimeResult::InvalidDatetime;
    };
    let datetime: DateTime<FixedOffset> = DateTime::from_naive_utc_and_offset(
        naive - offset,
        offset,
    );

    let chrono_fmt = python_to_chrono_format(fmt);
    let formatted = datetime.format(&chrono_fmt).to_string();

    if buf.try_push_str(&formatted).is_ok() {
        StrftimeResult::Ok
    } else {
        StrftimeResult::BufferTooSmall
    }
}

pub mod datetime_dumper {
    use pyo3::prelude::*;
    use pyo3::types::{PyDateTime, PyDateAccess, PyString, PyTimeAccess, PyTzInfoAccess};

    use super::{
        extract_components, field_error, format_iso, format_strftime, get_tz_offset_seconds,
        json_field_error, DateTimeComponents, DateTimeIsoBuf, DateTimeStrftimeBuf, DumpContext,
        StrftimeResult, BUFFER_ERROR_MSG, DATETIME_ERROR,
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
        datetime_format.map_or_else(
            || {
                let mut buf = DateTimeIsoBuf::new();
                format_iso(&mut buf, dt);
                Ok(PyString::new(py, &buf).into_any().unbind())
            },
            |fmt| {
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
            },
        )
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
            let mut buf = DateTimeStrftimeBuf::new();
            match format_strftime(&mut buf, &components, fmt) {
                StrftimeResult::Ok => serializer.serialize_str(&buf),
                _ => Err(S::Error::custom(json_field_error(field_name, DATETIME_ERROR))),
            }
        } else {
            let mut buf = DateTimeIsoBuf::new();
            format_iso(&mut buf, &components);
            serializer.serialize_str(&buf)
        }
    }
}

pub mod datetime_loader {
    use pyo3::prelude::*;
    use pyo3::types::PyString;
    use serde::de;

    use super::{
        create_pydatetime_from_chrono, field_error, parse_datetime_with_format,
        parse_rfc3339_datetime, DATETIME_ERROR,
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
        let s = value.cast::<PyString>().map_err(|_| datetime_err())?;
        let s_str = s.to_str()?;

        if let Some(fmt) = datetime_format {
            if let Some(dt) = parse_datetime_with_format(s_str, fmt) {
                return create_pydatetime_from_chrono(ctx.py, dt)
                    .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
            }
            return Err(datetime_err());
        }

        if let Some(dt) = parse_rfc3339_datetime(s_str) {
            return create_pydatetime_from_chrono(ctx.py, dt)
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
        if let Some(fmt) = format {
            if let Some(dt) = parse_datetime_with_format(s, fmt) {
                return create_pydatetime_from_chrono(py, dt).map_err(de::Error::custom);
            }
            return Err(de::Error::custom(err_msg));
        }
        parse_rfc3339_datetime(s)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|dt| create_pydatetime_from_chrono(py, dt).map_err(de::Error::custom))
    }
}
