use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::container::{StrEnumDumperData, StrEnumLoaderData};
use crate::error::{DumpError, LoadError};

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    data: &StrEnumLoaderData,
) -> Result<Py<PyAny>, LoadError> {
    let py = value.py();

    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
    {
        for (k, member) in &data.values {
            if k == s {
                return Ok(member.clone_ref(py));
            }
        }
    }

    let value_str = value
        .str()
        .map_or_else(|_| "?".to_string(), |s| s.to_string());
    let allowed: Vec<String> = data.values.iter().map(|(k, _)| format!("'{k}'")).collect();
    let err_msg = format!(
        "Not a valid choice: '{}'. Allowed values: [{}]",
        value_str,
        allowed.join(", ")
    );
    Err(LoadError::simple(&err_msg))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    data: &StrEnumDumperData,
) -> Result<Py<PyAny>, DumpError> {
    let py = value.py();

    if !value
        .is_instance(data.enum_cls.bind(py))
        .unwrap_or(false)
    {
        let msg = format!(
            "Invalid enum type. Expected {}.",
            data.enum_name.as_deref().unwrap_or("enum")
        );
        return Err(DumpError::simple(&msg));
    }

    let enum_value = value
        .getattr("value")
        .map_err(|e| DumpError::simple(&e.to_string()))?;

    Ok(enum_value.unbind())
}
