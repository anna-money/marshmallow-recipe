use pyo3::prelude::*;
use pyo3::types::PyInt;

use crate::container::{IntEnumDumperData, IntEnumLoaderData};
use crate::error::{DumpError, LoadError};

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    data: &IntEnumLoaderData,
) -> Result<Py<PyAny>, LoadError> {
    let py = value.py();

    if value.is_instance_of::<PyInt>()
        && let Ok(i) = value.extract::<i64>()
    {
        for (k, member) in &data.values {
            if *k == i {
                return Ok(member.clone_ref(py));
            }
        }
    }

    let value_str = value
        .str()
        .map_or_else(|_| "?".to_string(), |s| s.to_string());
    let valid_values: Vec<String> = data.values.iter().map(|(k, _)| k.to_string()).collect();
    let err_msg = format!(
        "Not a valid choice: '{}'. Allowed values: [{}]",
        value_str,
        valid_values.join(", ")
    );
    Err(LoadError::simple(&err_msg))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    data: &IntEnumDumperData,
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
