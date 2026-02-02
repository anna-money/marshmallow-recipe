use chrono::NaiveTime;
use pyo3::conversion::IntoPyObjectExt;
use pyo3::types::{PyString, PyTime};
use serde::de;
use serde::ser::Error as SerError;
use serde::Serialize;

use super::helpers::{field_error, json_field_error, TIME_ERROR};
use crate::types::{DumpContext, LoadContext};

pub mod time_dumper {
    use super::{
        field_error, json_field_error, DumpContext, NaiveTime, PyString, PyTime, SerError,
        Serialize, TIME_ERROR,
    };
    use pyo3::prelude::*;

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
        let t = value.extract::<NaiveTime>().map_err(|_| field_error(ctx.py, field_name, TIME_ERROR))?;
        Ok(PyString::new(ctx.py, &t.to_string()).into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        let t = value.extract::<NaiveTime>().map_err(|_| S::Error::custom(json_field_error(field_name, TIME_ERROR)))?;
        t.serialize(serializer)
    }
}

pub mod time_loader {
    use super::{de, field_error, IntoPyObjectExt, LoadContext, NaiveTime, PyString, TIME_ERROR};
    use pyo3::prelude::*;

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
        if let Ok(t) = s_str.parse::<NaiveTime>() {
            return t.into_py_any(ctx.py)
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }
        Err(time_err())
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        s.parse::<NaiveTime>()
            .map_err(|_| de::Error::custom(err_msg))
            .and_then(|t| t.into_py_any(py).map_err(de::Error::custom))
    }
}
