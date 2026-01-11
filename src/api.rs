use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};

use crate::cache::SCHEMA_CACHE;
use crate::encoding::{decode_to_utf8_bytes, encode_from_utf8_bytes};

#[pyfunction]
#[pyo3(signature = (schema_id, json_bytes, post_loads=None, decimal_places=None, encoding="utf-8"))]
pub fn load_from_bytes(
    py: Python,
    schema_id: u64,
    json_bytes: &[u8],
    post_loads: Option<&Bound<'_, PyDict>>,
    decimal_places: Option<i32>,
    encoding: &str,
) -> PyResult<Py<PyAny>> {
    let cache = SCHEMA_CACHE.read().unwrap_or_else(std::sync::PoisonError::into_inner);
    let descriptor = cache.get(&schema_id).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Schema {schema_id} not registered"))
    })?;

    let utf8_bytes = decode_to_utf8_bytes(json_bytes, encoding)?;
    crate::deserialize_bytes::load_from_bytes(py, &utf8_bytes, descriptor, post_loads, decimal_places)
}

#[pyfunction]
#[pyo3(signature = (schema_id, obj, none_value_handling=None, decimal_places=None, encoding="utf-8"))]
pub fn dump_to_bytes(
    py: Python,
    schema_id: u64,
    obj: &Bound<'_, PyAny>,
    none_value_handling: Option<&str>,
    decimal_places: Option<i32>,
    encoding: &str,
) -> PyResult<Py<PyBytes>> {
    let cache = SCHEMA_CACHE.read().unwrap_or_else(std::sync::PoisonError::into_inner);
    let descriptor = cache.get(&schema_id).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Schema {schema_id} not registered"))
    })?;

    let json_bytes = crate::serialize_bytes::dump_to_bytes(py, obj, descriptor, none_value_handling, decimal_places)?;
    let output_bytes = encode_from_utf8_bytes(&json_bytes, encoding)?;
    Ok(PyBytes::new(py, &output_bytes).unbind())
}

#[pyfunction]
#[pyo3(signature = (schema_id, data, post_loads=None, decimal_places=None))]
pub fn load(
    py: Python,
    schema_id: u64,
    data: &Bound<'_, PyAny>,
    post_loads: Option<&Bound<'_, PyDict>>,
    decimal_places: Option<i32>,
) -> PyResult<Py<PyAny>> {
    let cache = SCHEMA_CACHE.read().unwrap_or_else(std::sync::PoisonError::into_inner);
    let descriptor = cache.get(&schema_id).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Schema {schema_id} not registered"))
    })?;

    crate::deserialize::load(py, data, descriptor, post_loads, decimal_places)
}

#[pyfunction]
#[pyo3(signature = (schema_id, obj, none_value_handling=None, decimal_places=None))]
pub fn dump(
    py: Python,
    schema_id: u64,
    obj: &Bound<'_, PyAny>,
    none_value_handling: Option<&str>,
    decimal_places: Option<i32>,
) -> PyResult<Py<PyAny>> {
    let cache = SCHEMA_CACHE.read().unwrap_or_else(std::sync::PoisonError::into_inner);
    let descriptor = cache.get(&schema_id).ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Schema {schema_id} not registered"))
    })?;

    crate::serialize::dump(py, obj, descriptor, none_value_handling, decimal_places)
}
