use super::helpers::{field_error, json_field_error, UUID_ERROR};

pub mod uuid_dumper {
    use pyo3::prelude::*;
    use pyo3::types::PyString;
    use serde::ser::Error;

    use super::{field_error, json_field_error, UUID_ERROR};
    use crate::types::DumpContext;

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        value.extract::<uuid::Uuid>().is_ok()
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let uuid: uuid::Uuid = value
            .extract()
            .map_err(|_| field_error(ctx.py, field_name, UUID_ERROR))?;
        let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
        let s = uuid.hyphenated().encode_lower(&mut buf);
        Ok(PyString::new(ctx.py, s).into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::Serialize;
        let uuid: uuid::Uuid = value
            .extract()
            .map_err(|_| S::Error::custom(json_field_error(field_name, UUID_ERROR)))?;
        uuid.serialize(serializer)
    }
}

pub mod uuid_loader {
    use pyo3::prelude::*;
    use pyo3::types::PyString;
    use serde::de;

    use super::{field_error, UUID_ERROR};
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        if let Ok(uuid) = value.extract::<uuid::Uuid>() {
            return uuid
                .into_pyobject(ctx.py)
                .map(|b| b.into_any().unbind())
                .map_err(|e| field_error(ctx.py, field_name, &e.to_string()));
        }

        let uuid_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(UUID_ERROR));
        let s = value.cast::<PyString>().map_err(|_| uuid_err())?;
        let s_str = s.to_str()?;
        let uuid = uuid::Uuid::parse_str(s_str).map_err(|_| uuid_err())?;
        uuid.into_pyobject(ctx.py)
            .map(|b| b.into_any().unbind())
            .map_err(|e| field_error(ctx.py, field_name, &e.to_string()))
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(py: Python, s: &str, err_msg: &str) -> Result<Py<PyAny>, E> {
        let uuid = uuid::Uuid::parse_str(s).map_err(|_| de::Error::custom(err_msg))?;
        uuid.into_pyobject(py)
            .map(|b| b.into_any().unbind())
            .map_err(de::Error::custom)
    }
}
