use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt};
use serde_json::Value;

use super::helpers::{field_error, json_field_error, INT_ERROR};
use crate::types::SerializeContext;

pub mod int_serializer {
    use super::*;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
            return Err(field_error(ctx.py, field_name, INT_ERROR));
        }
        Ok(value.clone().unbind())
    }

    #[inline]
    pub fn serialize_to_json(
        value: &Bound<'_, PyAny>,
        field_name: &str,
    ) -> Result<Value, String> {
        if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
            return Err(json_field_error(field_name, INT_ERROR));
        }
        if let Ok(i) = value.extract::<i64>() {
            Ok(Value::Number(i.into()))
        } else if let Ok(u) = value.extract::<u64>() {
            Ok(Value::Number(u.into()))
        } else {
            let s: String = value.str().map_err(|e: PyErr| e.to_string())?.extract().map_err(|e: PyErr| e.to_string())?;
            let num = serde_json::Number::from_string_unchecked(s);
            Ok(Value::Number(num))
        }
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        use serde::Serialize;
        if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
            return Err(S::Error::custom(json_field_error(field_name, INT_ERROR)));
        }
        if let Ok(i) = value.extract::<i64>() {
            serializer.serialize_i64(i)
        } else if let Ok(u) = value.extract::<u64>() {
            serializer.serialize_u64(u)
        } else {
            let s: String = value.str().map_err(|e| S::Error::custom(e.to_string()))?
                .extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
            let num = serde_json::Number::from_string_unchecked(s);
            num.serialize(serializer)
        }
    }
}

pub mod int_deserializer {
    use super::*;
    use crate::types::LoadContext;
    use pyo3::conversion::IntoPyObjectExt;
    use serde::de;

    #[inline]
    pub fn deserialize_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
            Ok(value.clone().unbind())
        } else {
            Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(INT_ERROR)))
        }
    }

    #[inline]
    pub fn deserialize_from_i64<E: de::Error>(py: Python, v: i64) -> Result<Py<PyAny>, E> {
        v.into_py_any(py).map_err(de::Error::custom)
    }

    #[inline]
    pub fn deserialize_from_u64<E: de::Error>(py: Python, v: u64) -> Result<Py<PyAny>, E> {
        v.into_py_any(py).map_err(de::Error::custom)
    }

    #[inline]
    pub fn deserialize_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        s.parse::<i64>()
            .map_err(|_| de::Error::custom(err_msg))
            .and_then(|i| i.into_py_any(py).map_err(de::Error::custom))
    }
}
