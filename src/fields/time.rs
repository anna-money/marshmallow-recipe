use super::helpers::{field_error, json_field_error, TIME_ERROR};
use crate::types::DumpContext;
use crate::utils::parse_iso_time;

pub mod time_dumper {
    use std::fmt::Write;

    use arrayvec::ArrayString;
    use pyo3::prelude::*;
    use pyo3::types::{PyString, PyTime, PyTimeAccess};

    use super::{field_error, json_field_error, DumpContext, TIME_ERROR};

    pub type TimeBuf = ArrayString<15>;

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        value.is_instance_of::<PyTime>()
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyTime>() {
            return Err(field_error(ctx.py, field_name, TIME_ERROR));
        }
        let t: &Bound<'_, PyTime> = value.cast()?;
        let mut buf = TimeBuf::new();
        if t.get_microsecond() > 0 {
            write!(buf, "{:02}:{:02}:{:02}.{:06}", t.get_hour(), t.get_minute(), t.get_second(), t.get_microsecond())
                .expect("Time max 15 chars: HH:MM:SS.ffffff");
        } else {
            write!(buf, "{:02}:{:02}:{:02}", t.get_hour(), t.get_minute(), t.get_second())
                .expect("Time max 15 chars: HH:MM:SS.ffffff");
        }
        Ok(PyString::new(ctx.py, &buf).into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance_of::<PyTime>() {
            return Err(S::Error::custom(json_field_error(field_name, TIME_ERROR)));
        }
        let t: &Bound<'_, PyTime> = value.cast().map_err(|e| S::Error::custom(e.to_string()))?;
        let mut buf = TimeBuf::new();
        if t.get_microsecond() > 0 {
            write!(buf, "{:02}:{:02}:{:02}.{:06}", t.get_hour(), t.get_minute(), t.get_second(), t.get_microsecond())
                .expect("Time max 15 chars: HH:MM:SS.ffffff");
        } else {
            write!(buf, "{:02}:{:02}:{:02}", t.get_hour(), t.get_minute(), t.get_second())
                .expect("Time max 15 chars: HH:MM:SS.ffffff");
        }
        serializer.serialize_str(&buf)
    }
}

pub mod time_loader {
    use pyo3::conversion::IntoPyObjectExt;
    use pyo3::prelude::*;
    use pyo3::types::PyString;
    use serde::de;

    use super::{field_error, parse_iso_time, TIME_ERROR};
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        let time_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(TIME_ERROR));
        let s = value.cast::<PyString>().map_err(|_| time_err())?;
        let s_str = s.to_str()?;
        if let Some(t) = parse_iso_time(s_str) {
            return t.into_py_any(ctx.py)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }
        Err(time_err())
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        parse_iso_time(s)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|t| t.into_py_any(py).map_err(de::Error::custom))
    }
}
