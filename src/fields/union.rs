use super::helpers::{field_error, UNION_ERROR};
use crate::types::DumpContext;

pub mod union_dumper {
    use pyo3::prelude::*;

    use super::DumpContext;
    use crate::dumper::Dumper;

    #[inline]
    pub fn can_dump<'py>(
        value: &Bound<'py, PyAny>,
        ctx: &DumpContext<'_, 'py>,
        variants: &[Dumper],
    ) -> bool {
        variants.iter().any(|variant| variant.can_dump(value, ctx))
    }

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
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, '_>,
        variants: &[Dumper],
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;

        for variant in variants {
            if variant.can_dump(value, ctx) {
                return variant.dump(value, field_name, ctx, serializer);
            }
        }
        Err(S::Error::custom(format!(
            "Value does not match any union variant for field '{field_name}'"
        )))
    }
}

pub mod union_loader {
    use pyo3::prelude::*;

    use super::{field_error, UNION_ERROR};
    use crate::loader::Loader;
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
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
