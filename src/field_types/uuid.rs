use pyo3::prelude::*;
use pyo3::types::PyString;
use serde_json::Value;

use super::helpers::{field_error, json_field_error, UUID_ERROR};
use crate::cache::get_cached_types;
use crate::types::SerializeContext;

pub mod uuid_serializer {
    use super::*;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let cached = get_cached_types(ctx.py)?;
        if !value.is_instance(cached.uuid_cls.bind(ctx.py))? {
            return Err(field_error(ctx.py, field_name, UUID_ERROR));
        }
        let uuid_int: u128 = value.getattr(cached.str_int.bind(ctx.py))?.extract()?;
        let uuid = uuid::Uuid::from_u128(uuid_int);
        let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
        let s = uuid.hyphenated().encode_lower(&mut buf);
        Ok(PyString::new(ctx.py, s).into_any().unbind())
    }

    #[inline]
    pub fn serialize_to_json<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> Result<Value, String> {
        let cached = get_cached_types(ctx.py).map_err(|e| e.to_string())?;
        if !value.is_instance(cached.uuid_cls.bind(ctx.py)).map_err(|e| e.to_string())? {
            return Err(json_field_error(field_name, UUID_ERROR));
        }
        let uuid_int: u128 = value.getattr(cached.str_int.bind(ctx.py)).map_err(|e: PyErr| e.to_string())?.extract().map_err(|e: PyErr| e.to_string())?;
        let uuid = uuid::Uuid::from_u128(uuid_int);
        let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
        let s = uuid.hyphenated().encode_lower(&mut buf);
        Ok(Value::String(s.to_string()))
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, '_>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        let cached = get_cached_types(ctx.py).map_err(|e| S::Error::custom(e.to_string()))?;
        if !value.is_instance(cached.uuid_cls.bind(ctx.py)).map_err(|e| S::Error::custom(e.to_string()))? {
            return Err(S::Error::custom(json_field_error(field_name, UUID_ERROR)));
        }
        let uuid_int: u128 = value.getattr(cached.str_int.bind(ctx.py)).map_err(|e| S::Error::custom(e.to_string()))?
            .extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
        let uuid = uuid::Uuid::from_u128(uuid_int);
        let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
        let s = uuid.hyphenated().encode_lower(&mut buf);
        serializer.serialize_str(s)
    }
}

pub mod uuid_deserializer {
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
        let cached = get_cached_types(ctx.py)?;
        let uuid_cls = cached.uuid_cls.bind(ctx.py);
        if value.is_instance(uuid_cls)? {
            return Ok(value.clone().unbind());
        }
        let uuid_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(UUID_ERROR));
        let s = value.cast::<PyString>().map_err(|_| uuid_err())?;
        let s_str = s.to_str()?;
        uuid::Uuid::parse_str(s_str)
            .map_err(|_| uuid_err())
            .and_then(|uuid| cached.create_uuid_fast(ctx.py, uuid.as_u128()))
    }

    #[inline]
    pub fn deserialize_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        let cached = get_cached_types(py).map_err(de::Error::custom)?;
        let uuid = uuid::Uuid::parse_str(s).map_err(|_| de::Error::custom(err_msg))?;
        cached.create_uuid_fast(py, uuid.as_u128()).map_err(de::Error::custom)
    }
}
