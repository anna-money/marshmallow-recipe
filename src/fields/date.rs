use super::helpers::{field_error, json_field_error, DATE_ERROR};
use crate::types::DumpContext;
use crate::utils::{create_pydate_from_chrono, parse_iso_date};

pub mod date_dumper {
    use std::fmt::Write;

    use arrayvec::ArrayString;
    use pyo3::prelude::*;
    use pyo3::types::{PyDate, PyDateAccess, PyString};

    use super::{field_error, json_field_error, DumpContext, DATE_ERROR};

    pub type DateBuf = ArrayString<10>;

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        value.is_instance_of::<PyDate>()
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDate>() {
            return Err(field_error(ctx.py, field_name, DATE_ERROR));
        }
        let d: &Bound<'_, PyDate> = value.cast()?;
        let mut buf = DateBuf::new();
        write!(buf, "{:04}-{:02}-{:02}", d.get_year(), d.get_month(), d.get_day())
            .expect("Date max 10 chars: YYYY-MM-DD");
        Ok(PyString::new(ctx.py, &buf).into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance_of::<PyDate>() {
            return Err(S::Error::custom(json_field_error(field_name, DATE_ERROR)));
        }
        let d: &Bound<'_, PyDate> = value.cast().map_err(|e| S::Error::custom(e.to_string()))?;
        let mut buf = DateBuf::new();
        write!(buf, "{:04}-{:02}-{:02}", d.get_year(), d.get_month(), d.get_day())
            .expect("Date max 10 chars: YYYY-MM-DD");
        serializer.serialize_str(&buf)
    }
}

pub mod date_loader {
    use pyo3::prelude::*;
    use pyo3::types::PyString;
    use serde::de;

    use super::{create_pydate_from_chrono, field_error, parse_iso_date, DATE_ERROR};
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        let date_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(DATE_ERROR));
        let s = value.cast::<PyString>().map_err(|_| date_err())?;
        let s_str = s.to_str()?;
        if let Some(d) = parse_iso_date(s_str) {
            return create_pydate_from_chrono(ctx.py, d)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }
        Err(date_err())
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        parse_iso_date(s)
            .ok_or_else(|| de::Error::custom(err_msg))
            .and_then(|d| create_pydate_from_chrono(py, d).map_err(de::Error::custom))
    }
}
