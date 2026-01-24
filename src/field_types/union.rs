use pyo3::prelude::*;
use serde_json::Value;

use super::helpers::{field_error, UNION_ERROR};
use crate::types::DumpContext;

pub mod union_dumper {
    use super::*;
    use crate::serializer::Dumper;

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        variants: &[Dumper],
    ) -> PyResult<Py<PyAny>> {
        for variant in variants {
            if let Ok(result) = variant.dump_to_dict(value, field_name, ctx) {
                return Ok(result);
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "Value does not match any union variant for field '{field_name}'"
        )))
    }

    #[inline]
    pub fn dump_to_serde_value<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        variants: &[Dumper],
    ) -> Result<Value, String> {
        for variant in variants {
            if let Ok(result) = variant.dump_to_serde_value(value, field_name, ctx) {
                return Ok(result);
            }
        }
        Err(format!("Value does not match any union variant for field '{field_name}'"))
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, '_>,
        variants: &[Dumper],
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;

        let mut matched_idx: Option<usize> = None;
        for (idx, variant) in variants.iter().enumerate() {
            if variant.dump_to_serde_value(value, field_name, ctx).is_ok() {
                matched_idx = Some(idx);
                break;
            }
        }

        #[allow(clippy::option_if_let_else)]
        match matched_idx {
            Some(idx) => variants[idx].dump(value, field_name, ctx, serializer),
            None => Err(S::Error::custom(format!(
                "Value does not match any union variant for field '{field_name}'"
            ))),
        }
    }
}

pub mod union_loader {
    use super::*;
    use crate::deserializer::Loader;
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
        variants: &[Loader],
    ) -> PyResult<Py<PyAny>> {
        for variant in variants {
            if let Ok(result) = variant.load_from_dict(value, field_name, invalid_error, ctx) {
                return Ok(result);
            }
        }
        Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(UNION_ERROR)))
    }
}
