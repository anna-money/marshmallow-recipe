use chrono::NaiveDate;
use pyo3::conversion::IntoPyObjectExt;
use pyo3::types::{PyDate, PyString};
use serde::de;
use serde::ser::Error as SerError;
use serde::Serialize;

use super::helpers::{field_error, json_field_error, DATE_ERROR};
use crate::types::{DumpContext, LoadContext};

pub mod date_dumper {
    use super::{
        field_error, json_field_error, DumpContext, NaiveDate, PyDate, PyString, SerError,
        Serialize, DATE_ERROR,
    };
    use pyo3::prelude::*;

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
        let d = value.extract::<NaiveDate>().map_err(|_| field_error(ctx.py, field_name, DATE_ERROR))?;
        Ok(PyString::new(ctx.py, &d.to_string()).into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        let d = value.extract::<NaiveDate>().map_err(|_| S::Error::custom(json_field_error(field_name, DATE_ERROR)))?;
        d.serialize(serializer)
    }
}

pub mod date_loader {
    use super::{de, field_error, IntoPyObjectExt, LoadContext, NaiveDate, PyString, DATE_ERROR};
    use pyo3::prelude::*;

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
        if let Ok(d) = s_str.parse::<NaiveDate>() {
            return d.into_py_any(ctx.py)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }
        Err(date_err())
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        s.parse::<NaiveDate>()
            .map_err(|_| de::Error::custom(err_msg))
            .and_then(|d| d.into_py_any(py).map_err(de::Error::custom))
    }
}
