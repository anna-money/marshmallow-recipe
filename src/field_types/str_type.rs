use pyo3::prelude::*;
use pyo3::types::PyString;
use serde_json::Value;

use super::helpers::{field_error, json_field_error, STR_ERROR};
use crate::types::DumpContext;

pub mod str_dumper {
    use super::*;

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        strip_whitespaces: bool,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyString>() {
            return Err(field_error(ctx.py, field_name, STR_ERROR));
        }
        if strip_whitespaces {
            let s: String = value.extract()?;
            Ok(PyString::new(ctx.py, s.trim()).into_any().unbind())
        } else {
            Ok(value.clone().unbind())
        }
    }

    #[inline]
    pub fn dump_to_serde_value(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        strip_whitespaces: bool,
    ) -> Result<Value, String> {
        if !value.is_instance_of::<PyString>() {
            return Err(json_field_error(field_name, STR_ERROR));
        }
        let py_str = value.cast::<PyString>().map_err(|e| e.to_string())?;
        let s = py_str.to_str().map_err(|e| e.to_string())?;
        if strip_whitespaces {
            Ok(Value::String(s.trim().to_string()))
        } else {
            Ok(Value::String(s.to_string()))
        }
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        strip_whitespaces: bool,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance_of::<PyString>() {
            return Err(S::Error::custom(json_field_error(field_name, STR_ERROR)));
        }
        let py_str = value.cast::<PyString>().map_err(|e| S::Error::custom(e.to_string()))?;
        let s = py_str.to_str().map_err(|e| S::Error::custom(e.to_string()))?;
        if strip_whitespaces {
            serializer.serialize_str(s.trim())
        } else {
            serializer.serialize_str(s)
        }
    }
}

pub mod str_loader {
    use super::*;
    use crate::types::LoadContext;
    use pyo3::conversion::IntoPyObjectExt;
    use serde::de;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
        strip_whitespaces: bool,
    ) -> PyResult<Py<PyAny>> {
        if let Ok(s) = value.cast::<PyString>() {
            if strip_whitespaces {
                let trimmed = s.to_str()?.trim();
                Ok(PyString::new(ctx.py, trimmed).into_any().unbind())
            } else {
                Ok(value.clone().unbind())
            }
        } else {
            Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(STR_ERROR)))
        }
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(
        py: Python,
        s: &str,
        strip_whitespaces: bool,
    ) -> Result<Py<PyAny>, E> {
        let s = if strip_whitespaces { s.trim() } else { s };
        s.into_py_any(py).map_err(de::Error::custom)
    }
}
