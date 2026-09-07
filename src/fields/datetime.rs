use chrono::{DateTime, Duration, FixedOffset, NaiveDate, NaiveDateTime, NaiveTime};
use pyo3::conversion::IntoPyObjectExt;
use pyo3::exceptions::PyValueError;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{
    PyBool, PyDateAccess, PyDateTime, PyFloat, PyInt, PyString, PyTimeAccess, PyTzInfo,
    PyTzInfoAccess,
};

use crate::error::SerializationError;
use crate::utils::display_to_py;
use crate::utils::py_str;
use crate::utils::{parse_datetime_with_format, python_to_chrono_format};

const ISO_WITH_MICROS: &str = "%Y-%m-%dT%H:%M:%S%.6f%:z";
const ISO_WITHOUT_MICROS: &str = "%Y-%m-%dT%H:%M:%S%:z";

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
            if let Ok(py_str) = value.cast::<PyString>()
                && let Ok(s) = py_str.to_str()
                && let Ok(f) = s.trim().parse::<f64>()
                && f.is_finite()
            {
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
    as_string: bool,
    format: &DateTimeFormat,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    let dt = extract_datetime(value)
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    match format {
        DateTimeFormat::Iso => {
            let fmt = if dt.timestamp_subsec_micros() == 0 {
                ISO_WITHOUT_MICROS
            } else {
                ISO_WITH_MICROS
            };
            Ok(display_to_py::<40, _>(py, &dt.format(fmt)))
        }
        DateTimeFormat::Timestamp => {
            let ts = datetime_to_timestamp(&dt)
                .ok_or_else(|| SerializationError::Single(invalid_error.clone_ref(py)))?;
            let result = ts
                .into_py_any(py)
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            if as_string {
                return py_str(result.bind(py));
            }
            Ok(result)
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
    let dt = value.cast::<PyDateTime>()?;
    let naive = extract_naive_datetime(dt)?;
    let Some(tzinfo) = dt.get_tzinfo() else {
        return Ok(naive.and_utc().fixed_offset());
    };
    if tzinfo.is(PyTzInfo::utc(dt.py())?) {
        return Ok(naive.and_utc().fixed_offset());
    }
    let utcoffset = tzinfo.call_method1(intern!(dt.py(), "utcoffset"), (dt,))?;
    if utcoffset.is_none() {
        return Err(PyValueError::new_err("utcoffset is None"));
    }
    let delta: Duration = utcoffset.extract()?;
    let offset = i32::try_from(delta.num_seconds())
        .ok()
        .and_then(FixedOffset::east_opt)
        .ok_or_else(|| PyValueError::new_err("utcoffset is out of bounds"))?;
    naive
        .and_local_timezone(offset)
        .single()
        .ok_or_else(|| PyValueError::new_err("datetime is out of bounds"))
}

fn extract_naive_datetime(dt: &Bound<'_, PyDateTime>) -> PyResult<NaiveDateTime> {
    let date = NaiveDate::from_ymd_opt(dt.get_year(), dt.get_month().into(), dt.get_day().into())
        .ok_or_else(|| PyValueError::new_err("date is out of bounds"))?;
    let time = NaiveTime::from_hms_micro_opt(
        dt.get_hour().into(),
        dt.get_minute().into(),
        dt.get_second().into(),
        dt.get_microsecond(),
    )
    .ok_or_else(|| PyValueError::new_err("time is out of bounds"))?;
    Ok(NaiveDateTime::new(date, time))
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
