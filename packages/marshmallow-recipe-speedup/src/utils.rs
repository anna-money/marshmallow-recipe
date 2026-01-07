use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;

pub fn pyany_to_json_value(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if let Ok(s) = obj.extract::<String>() {
        return Ok(Value::String(s));
    }
    if let Ok(list) = obj.cast::<PyList>() {
        let items: Vec<Value> = list
            .iter()
            .map(|item| pyany_to_json_value(&item).unwrap_or_else(|_| Value::String("Validation error".to_string())))
            .collect();
        return Ok(Value::Array(items));
    }
    if let Ok(dict) = obj.cast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (key, value) in dict.iter() {
            let key_str = key.extract::<String>().unwrap_or_else(|_| key.to_string());
            let val = pyany_to_json_value(&value).unwrap_or_else(|_| Value::String("Validation error".to_string()));
            map.insert(key_str, val);
        }
        return Ok(Value::Object(map));
    }
    Ok(Value::String(obj.to_string()))
}
