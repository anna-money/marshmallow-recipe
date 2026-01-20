use std::fmt::Write;

use pyo3::prelude::*;
use pyo3::types::{PyString, PyTime, PyTimeAccess};
use serde_json::Value;

use super::helpers::{field_error, json_field_error, TIME_ERROR};
use crate::types::SerializeContext;
use crate::utils::{create_pytime_from_speedate, parse_iso_time};

pub mod time_serializer {
    use super::*;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyTime>() {
            return Err(field_error(ctx.py, field_name, TIME_ERROR));
        }
        let t: &Bound<'_, PyTime> = value.cast()?;
        let mut buf = arrayvec::ArrayString::<15>::new();
        if t.get_microsecond() > 0 {
            write!(buf, "{:02}:{:02}:{:02}.{:06}", t.get_hour(), t.get_minute(), t.get_second(), t.get_microsecond()).unwrap();
        } else {
            write!(buf, "{:02}:{:02}:{:02}", t.get_hour(), t.get_minute(), t.get_second()).unwrap();
        }
        Ok(PyString::new(ctx.py, &buf).into_any().unbind())
    }

    #[inline]
    pub fn serialize_to_json(
        value: &Bound<'_, PyAny>,
        field_name: &str,
    ) -> Result<Value, String> {
        if !value.is_instance_of::<PyTime>() {
            return Err(json_field_error(field_name, TIME_ERROR));
        }
        let t: &Bound<'_, PyTime> = value.cast().map_err(|e| e.to_string())?;
        let mut buf = arrayvec::ArrayString::<15>::new();
        if t.get_microsecond() > 0 {
            write!(buf, "{:02}:{:02}:{:02}.{:06}", t.get_hour(), t.get_minute(), t.get_second(), t.get_microsecond()).unwrap();
        } else {
            write!(buf, "{:02}:{:02}:{:02}", t.get_hour(), t.get_minute(), t.get_second()).unwrap();
        }
        Ok(Value::String(buf.to_string()))
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance_of::<PyTime>() {
            return Err(S::Error::custom(json_field_error(field_name, TIME_ERROR)));
        }
        let t: &Bound<'_, PyTime> = value.cast().map_err(|e| S::Error::custom(e.to_string()))?;
        let mut buf = arrayvec::ArrayString::<15>::new();
        if t.get_microsecond() > 0 {
            write!(buf, "{:02}:{:02}:{:02}.{:06}", t.get_hour(), t.get_minute(), t.get_second(), t.get_microsecond()).unwrap();
        } else {
            write!(buf, "{:02}:{:02}:{:02}", t.get_hour(), t.get_minute(), t.get_second()).unwrap();
        }
        serializer.serialize_str(&buf)
    }
}

pub mod time_deserializer {
    use super::*;
    use crate::types::LoadContext;
    use serde::de;

    #[inline]
    pub fn deserialize_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let time_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(TIME_ERROR));
        let s = value.cast::<PyString>().map_err(|_| time_err())?;
        let s_str = s.to_str()?;
        if let Some(t) = parse_iso_time(s_str) {
            return create_pytime_from_speedate(ctx.py, &t)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }
        Err(time_err())
    }

    #[inline]
    pub fn deserialize_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        parse_iso_time(s)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|t| create_pytime_from_speedate(py, &t).map_err(de::Error::custom))
    }
}
