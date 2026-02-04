use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::container::{StrEnumDumperData, StrEnumLoaderData};
use crate::error::{DumpError, LoadError};

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    data: &StrEnumLoaderData,
) -> Result<Py<PyAny>, LoadError> {
    let str_value = value.as_str();
    if let Some(s) = str_value {
        for (k, member) in &data.values {
            if k == s {
                return Ok(member.clone_ref(py));
            }
        }
    }

    let value_str = if let Some(s) = str_value {
        s.to_string()
    } else if let Some(i) = value.as_i64() {
        i.to_string()
    } else if let Some(f) = value.as_f64() {
        f.to_string()
    } else if let Some(b) = value.as_bool() {
        b.to_string()
    } else {
        "null".to_string()
    };

    let allowed: Vec<String> = data.values.iter().map(|(k, _)| format!("'{k}'")).collect();
    let err_msg = format!(
        "Not a valid choice: '{value_str}'. Allowed values: [{}]",
        allowed.join(", ")
    );
    Err(LoadError::simple(&err_msg))
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    data: &StrEnumLoaderData,
) -> Result<Py<PyAny>, LoadError> {
    let py = value.py();

    if let Ok(py_str) = value.cast::<PyString>() {
        if let Ok(s) = py_str.to_str() {
            for (k, member) in &data.values {
                if k == s {
                    return Ok(member.clone_ref(py));
                }
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

pub fn dump(
    value: &Bound<'_, PyAny>,
    data: &StrEnumDumperData,
) -> Result<serde_json::Value, DumpError> {
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

    let s: String = enum_value
        .extract()
        .map_err(|e: PyErr| DumpError::simple(&e.to_string()))?;

    Ok(serde_json::Value::String(s))
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
