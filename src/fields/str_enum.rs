use super::helpers::field_error;
use crate::types::DumpContext;

pub mod str_enum_dumper {
    use pyo3::prelude::*;
    use pyo3::types::PyString;

    use super::{field_error, DumpContext};

    #[inline]
    pub fn can_dump<'py>(value: &Bound<'py, PyAny>, ctx: &DumpContext<'_, 'py>, enum_cls: &Py<PyAny>) -> bool {
        value.is_instance(enum_cls.bind(ctx.py)).unwrap_or(false)
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        enum_cls: &Py<PyAny>,
        enum_name: Option<&str>,
        enum_members_repr: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance(enum_cls.bind(ctx.py))? {
            let value_type_name: String = value.get_type().name()?.extract()?;
            let enum_name = enum_name.unwrap_or("Enum");
            let members_repr = enum_members_repr.unwrap_or("[]");
            let msg = format!("Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}");
            return Err(field_error(ctx.py, field_name, &msg));
        }
        Ok(value.cast::<PyString>()?.to_owned().into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        _field_name: &str,
        ctx: &DumpContext<'_, '_>,
        enum_cls: &Py<PyAny>,
        enum_name: Option<&str>,
        enum_members_repr: Option<&str>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance(enum_cls.bind(ctx.py)).map_err(|e| S::Error::custom(e.to_string()))? {
            let value_type_name: String = value.get_type().name().map_err(|e| S::Error::custom(e.to_string()))?
                .extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
            let enum_name = enum_name.unwrap_or("Enum");
            let members_repr = enum_members_repr.unwrap_or("[]");
            let msg = format!("Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}");
            return Err(S::Error::custom(format!("[\"{msg}\"]")));
        }
        let s = value.cast::<PyString>().map_err(|e| S::Error::custom(e.to_string()))?
            .to_str().map_err(|e| S::Error::custom(e.to_string()))?;
        serializer.serialize_str(s)
    }
}

pub mod str_enum_loader {
    use pyo3::prelude::*;
    use serde::de;

    use super::field_error;
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &LoadContext<'py>,
        values: &[(String, Py<PyAny>)],
    ) -> PyResult<Py<PyAny>> {
        let s: &str = value.extract().map_err(|_| {
            let msg = format_invalid_msg(value, values);
            field_error(ctx.py, field_name, &msg)
        })?;
        for (k, v) in values {
            if k == s {
                return Ok(v.clone_ref(ctx.py));
            }
        }
        let msg = format_invalid_msg(value, values);
        Err(field_error(ctx.py, field_name, &msg))
    }

    pub fn format_invalid_msg(value: &Bound<'_, PyAny>, values: &[(String, Py<PyAny>)]) -> String {
        let allowed = values.iter().map(|(k, _)| format!("'{k}'")).collect::<Vec<_>>().join(", ");
        let value_str = value.str().map_or_else(|_| "?".to_string(), |s| s.to_string());
        format!("Not a valid choice: '{value_str}'. Allowed values: [{allowed}]")
    }

    pub fn format_visit_error<V: std::fmt::Display>(v: V, values: &[(String, Py<PyAny>)], invalid_error: Option<&str>) -> String {
        invalid_error.map_or_else(
            || {
                let allowed: Vec<String> = values.iter().map(|(k, _)| format!("'{k}'")).collect();
                format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
            },
            ToString::to_string,
        )
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(
        py: Python,
        s: &str,
        values: &[(String, Py<PyAny>)],
        invalid_error: Option<&str>,
    ) -> Result<Py<PyAny>, E> {
        for (k, v) in values {
            if k == s {
                return Ok(v.clone_ref(py));
            }
        }
        let msg = format_visit_error(s, values, invalid_error);
        Err(de::Error::custom(msg))
    }
}

pub mod int_enum_dumper {
    use pyo3::prelude::*;
    use pyo3::types::PyInt;

    use super::{field_error, DumpContext};

    #[inline]
    pub fn can_dump<'py>(value: &Bound<'py, PyAny>, ctx: &DumpContext<'_, 'py>, enum_cls: &Py<PyAny>) -> bool {
        value.is_instance(enum_cls.bind(ctx.py)).unwrap_or(false)
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        enum_cls: &Py<PyAny>,
        enum_name: Option<&str>,
        enum_members_repr: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance(enum_cls.bind(ctx.py))? {
            let value_type_name: String = value.get_type().name()?.extract()?;
            let enum_name = enum_name.unwrap_or("Enum");
            let members_repr = enum_members_repr.unwrap_or("[]");
            let msg = format!("Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}");
            return Err(field_error(ctx.py, field_name, &msg));
        }
        Ok(value.cast::<PyInt>()?.to_owned().into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        _field_name: &str,
        ctx: &DumpContext<'_, '_>,
        enum_cls: &Py<PyAny>,
        enum_name: Option<&str>,
        enum_members_repr: Option<&str>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance(enum_cls.bind(ctx.py)).map_err(|e| S::Error::custom(e.to_string()))? {
            let value_type_name: String = value.get_type().name().map_err(|e| S::Error::custom(e.to_string()))?
                .extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
            let enum_name = enum_name.unwrap_or("Enum");
            let members_repr = enum_members_repr.unwrap_or("[]");
            let msg = format!("Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}");
            return Err(S::Error::custom(format!("[\"{msg}\"]")));
        }
        let i: i64 = value.extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
        serializer.serialize_i64(i)
    }
}
