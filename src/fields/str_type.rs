use super::helpers::{field_error, json_field_error, STR_ERROR};
use crate::types::DumpContext;

pub mod str_dumper {
    use pyo3::prelude::*;
    use pyo3::types::PyString;

    use super::{field_error, json_field_error, DumpContext, STR_ERROR};

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        value.cast::<PyString>().is_ok()
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        strip_whitespaces: bool,
    ) -> PyResult<Py<PyAny>> {
        let py_str = value
            .cast::<PyString>()
            .map_err(|_| field_error(ctx.py, field_name, STR_ERROR))?;
        if strip_whitespaces {
            let s = py_str.to_str()?;
            let trimmed = s.trim();
            if trimmed.len() == s.len() {
                Ok(value.clone().unbind())
            } else {
                Ok(PyString::new(ctx.py, trimmed).into_any().unbind())
            }
        } else {
            Ok(value.clone().unbind())
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
        let py_str = value
            .cast::<PyString>()
            .map_err(|_| S::Error::custom(json_field_error(field_name, STR_ERROR)))?;
        let s = py_str.to_str().map_err(|e| S::Error::custom(e.to_string()))?;
        if strip_whitespaces {
            serializer.serialize_str(s.trim())
        } else {
            serializer.serialize_str(s)
        }
    }
}

pub mod str_loader {
    use pyo3::conversion::IntoPyObjectExt;
    use pyo3::prelude::*;
    use pyo3::types::PyString;
    use serde::de;

    use super::{field_error, STR_ERROR};
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
        strip_whitespaces: bool,
    ) -> PyResult<Py<PyAny>> {
        if let Ok(py_str) = value.cast::<PyString>() {
            if strip_whitespaces {
                let s = py_str.to_str()?;
                let trimmed = s.trim();
                if trimmed.len() == s.len() {
                    Ok(value.clone().unbind())
                } else {
                    Ok(PyString::new(ctx.py, trimmed).into_any().unbind())
                }
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
