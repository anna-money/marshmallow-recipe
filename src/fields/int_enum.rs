use super::helpers::field_error;
use crate::types::LoadContext;

pub mod int_enum_loader {
    use pyo3::prelude::*;
    use serde::de;

    use super::{field_error, LoadContext};

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &LoadContext<'py>,
        values: &[(i64, Py<PyAny>)],
    ) -> PyResult<Py<PyAny>> {
        let i: i64 = value.extract().map_err(|_| {
            let msg = format_invalid_msg(value, values);
            field_error(ctx.py, field_name, &msg)
        })?;
        for (k, v) in values {
            if *k == i {
                return Ok(v.clone_ref(ctx.py));
            }
        }
        let msg = format_invalid_msg(value, values);
        Err(field_error(ctx.py, field_name, &msg))
    }

    pub fn format_invalid_msg(value: &Bound<'_, PyAny>, values: &[(i64, Py<PyAny>)]) -> String {
        let allowed = values.iter().map(|(k, _)| k.to_string()).collect::<Vec<_>>().join(", ");
        let value_str = value.str().map_or_else(|_| "?".to_string(), |s| s.to_string());
        format!("Not a valid choice: '{value_str}'. Allowed values: [{allowed}]")
    }

    pub fn format_visit_error<V: std::fmt::Display>(v: V, values: &[(i64, Py<PyAny>)], invalid_error: Option<&str>) -> String {
        invalid_error.map_or_else(
            || {
                let allowed: Vec<String> = values.iter().map(|(k, _)| k.to_string()).collect();
                format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
            },
            ToString::to_string,
        )
    }

    #[inline]
    pub fn load_from_i64<E: de::Error>(
        py: Python,
        v: i64,
        values: &[(i64, Py<PyAny>)],
        invalid_error: Option<&str>,
    ) -> Result<Py<PyAny>, E> {
        for (k, member) in values {
            if *k == v {
                return Ok(member.clone_ref(py));
            }
        }
        let msg = format_visit_error(v, values, invalid_error);
        Err(de::Error::custom(msg))
    }

    #[inline]
    pub fn load_from_u64<E: de::Error>(
        py: Python,
        v: u64,
        values: &[(i64, Py<PyAny>)],
        invalid_error: Option<&str>,
    ) -> Result<Py<PyAny>, E> {
        if let Ok(v_i64) = i64::try_from(v) {
            for (k, member) in values {
                if *k == v_i64 {
                    return Ok(member.clone_ref(py));
                }
            }
        }
        let msg = format_visit_error(v, values, invalid_error);
        Err(de::Error::custom(msg))
    }
}
