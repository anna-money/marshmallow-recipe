use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;

pub fn pyany_to_json_value(obj: &Bound<'_, PyAny>) -> Value {
    if let Ok(s) = obj.extract::<String>() {
        return Value::String(s);
    }
    if let Ok(list) = obj.cast::<PyList>() {
        let items: Vec<Value> = list.iter().map(|item| pyany_to_json_value(&item)).collect();
        return Value::Array(items);
    }
    if let Ok(dict) = obj.cast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (key, value) in dict.iter() {
            let key_str = key.extract::<String>().unwrap_or_else(|_| key.to_string());
            map.insert(key_str, pyany_to_json_value(&value));
        }
        return Value::Object(map);
    }
    Value::String(obj.to_string())
}
