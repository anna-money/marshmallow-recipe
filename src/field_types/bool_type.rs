use pyo3::prelude::*;
use pyo3::types::PyBool;
use serde_json::Value;

use super::helpers::{field_error, json_field_error, BOOL_ERROR};
use crate::types::DumpContext;

pub mod bool_dumper {
    use super::*;

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyBool>() {
            return Err(field_error(ctx.py, field_name, BOOL_ERROR));
        }
        Ok(value.clone().unbind())
    }

    #[inline]
    pub fn dump_to_serde_value(
        value: &Bound<'_, PyAny>,
        field_name: &str,
    ) -> Result<Value, String> {
        if !value.is_instance_of::<PyBool>() {
            return Err(json_field_error(field_name, BOOL_ERROR));
        }
        let b: bool = value.extract().map_err(|e: PyErr| e.to_string())?;
        Ok(Value::Bool(b))
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance_of::<PyBool>() {
            return Err(S::Error::custom(json_field_error(field_name, BOOL_ERROR)));
        }
        let b: bool = value.extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
        serializer.serialize_bool(b)
    }
}

pub mod bool_loader {
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
    ) -> PyResult<Py<PyAny>> {
        if value.is_instance_of::<PyBool>() {
            Ok(value.clone().unbind())
        } else {
            Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(BOOL_ERROR)))
        }
    }

    #[inline]
    pub fn load_from_bool<E: de::Error>(py: Python, v: bool) -> Result<Py<PyAny>, E> {
        v.into_py_any(py).map_err(de::Error::custom)
    }
}
