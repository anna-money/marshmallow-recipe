use pyo3::prelude::*;
use serde_json::Value;

use super::helpers::{field_error, UNION_ERROR};
use crate::types::SerializeContext;

pub mod union_serializer {
    use super::*;
    use crate::serializer::Serializer;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        variants: &[Serializer],
    ) -> PyResult<Py<PyAny>> {
        for variant in variants {
            if let Ok(result) = variant.serialize_to_dict(value, field_name, ctx) {
                return Ok(result);
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Value does not match any union variant for field '{field_name}'"
        )))
    }

    #[inline]
    pub fn serialize_to_json<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        variants: &[Serializer],
    ) -> Result<Value, String> {
        for variant in variants {
            if let Ok(result) = variant.serialize_to_json(value, field_name, ctx) {
                return Ok(result);
            }
        }
        Err(format!("Value does not match any union variant for field '{field_name}'"))
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, '_>,
        variants: &[Serializer],
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;

        let mut matched_idx: Option<usize> = None;
        for (idx, variant) in variants.iter().enumerate() {
            if variant.serialize_to_json(value, field_name, ctx).is_ok() {
                matched_idx = Some(idx);
                break;
            }
        }

        #[allow(clippy::option_if_let_else)]
        match matched_idx {
            Some(idx) => variants[idx].serialize(value, field_name, ctx, serializer),
            None => Err(S::Error::custom(format!(
                "Value does not match any union variant for field '{field_name}'"
            ))),
        }
    }
}

pub mod union_deserializer {
    use super::*;
    use crate::deserializer::Deserializer;
    use crate::types::LoadContext;

    #[inline]
    pub fn deserialize_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
        variants: &[Deserializer],
    ) -> PyResult<Py<PyAny>> {
        for variant in variants {
            if let Ok(result) = variant.deserialize_from_dict(value, field_name, invalid_error, ctx) {
                return Ok(result);
            }
        }
        Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(UNION_ERROR)))
    }
}
