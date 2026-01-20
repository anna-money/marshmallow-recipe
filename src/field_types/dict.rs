use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};
use serde_json::Value;

use super::helpers::{field_error, json_field_error, DICT_ERROR};
use crate::types::SerializeContext;
use crate::utils::{call_validator, pyany_to_json_value, wrap_err_dict};

pub mod dict_serializer {
    use super::*;
    use crate::serializer::Serializer;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        value_serializer: &Serializer,
        value_validator: Option<&Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDict>() {
            return Err(field_error(ctx.py, field_name, DICT_ERROR));
        }
        let dict = value.cast::<PyDict>()?;
        let result = PyDict::new(ctx.py);
        let mut value_errors: Option<Py<PyAny>> = None;

        for (k, v) in dict.iter() {
            if let Some(validator) = value_validator {
                if let Some(err) = call_validator(ctx.py, validator, &v)? {
                    let err_dict = value_errors.get_or_insert_with(|| PyDict::new(ctx.py).into_any().unbind());
                    err_dict.bind(ctx.py).cast::<PyDict>()?.set_item(&k, err)?;
                }
            }
            let key_str: String = k.extract()?;
            let serialized = serialize_item(value_serializer, &v, &key_str, ctx)?;
            result.set_item(k, serialized)?;
        }

        if let Some(ref errs) = value_errors {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                wrap_err_dict(ctx.py, field_name, errs.clone_ref(ctx.py)),
            ));
        }

        Ok(result.into_any().unbind())
    }

    fn serialize_item<'py>(
        value_serializer: &Serializer,
        value: &Bound<'py, PyAny>,
        key: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if value.is_none() {
            return Ok(ctx.py.None());
        }
        value_serializer.serialize_to_dict(value, key, ctx)
    }

    #[inline]
    pub fn serialize_to_json<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        value_serializer: &Serializer,
        value_validator: Option<&Py<PyAny>>,
    ) -> Result<Value, String> {
        if !value.is_instance_of::<PyDict>() {
            return Err(json_field_error(field_name, DICT_ERROR));
        }
        let dict = value.cast::<PyDict>().map_err(|e| e.to_string())?;

        if let Some(validator) = value_validator {
            for (k, v) in dict.iter() {
                let key = k.cast::<PyString>().map_err(|e| e.to_string())?
                    .to_str().map_err(|e| e.to_string())?;
                if let Some(errors) = call_validator(ctx.py, validator, &v).map_err(|e| e.to_string())? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut inner_map = serde_json::Map::new();
                    inner_map.insert(key.to_string(), errors_json);
                    let mut map = serde_json::Map::new();
                    map.insert(field_name.to_string(), Value::Object(inner_map));
                    return Err(Value::Object(map).to_string());
                }
            }
        }

        let mut result = serde_json::Map::new();
        for (k, v) in dict.iter() {
            let key = k.cast::<PyString>().map_err(|e| e.to_string())?
                .to_str().map_err(|e| e.to_string())?;
            let serialized = serialize_item_json(value_serializer, &v, key, ctx)?;
            result.insert(key.to_string(), serialized);
        }
        Ok(Value::Object(result))
    }

    fn serialize_item_json<'py>(
        value_serializer: &Serializer,
        value: &Bound<'py, PyAny>,
        key: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> Result<Value, String> {
        if value.is_none() {
            return Ok(Value::Null);
        }
        value_serializer.serialize_to_json(value, key, ctx)
    }

    struct ValueSerializer<'a, 'py> {
        value: &'a Bound<'py, PyAny>,
        inner: &'a Serializer,
        key: String,
        ctx: &'a SerializeContext<'a, 'py>,
    }

    impl serde::Serialize for ValueSerializer<'_, '_> {
        fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
            if self.value.is_none() {
                return serializer.serialize_none();
            }
            self.inner.serialize(self.value, &self.key, self.ctx, serializer)
        }
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, '_>,
        value_serializer: &Serializer,
        value_validator: Option<&Py<PyAny>>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::{Error, SerializeMap};

        if !value.is_instance_of::<PyDict>() {
            return Err(S::Error::custom(json_field_error(field_name, DICT_ERROR)));
        }
        let dict = value.cast::<PyDict>().map_err(|e| S::Error::custom(e.to_string()))?;

        if let Some(validator) = value_validator {
            for (k, v) in dict.iter() {
                let key = k.cast::<PyString>().map_err(|e| S::Error::custom(e.to_string()))?
                    .to_str().map_err(|e| S::Error::custom(e.to_string()))?;
                if let Some(errors) = call_validator(ctx.py, validator, &v).map_err(|e| S::Error::custom(e.to_string()))? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut inner_map = serde_json::Map::new();
                    inner_map.insert(key.to_string(), errors_json);
                    let mut map = serde_json::Map::new();
                    map.insert(field_name.to_string(), Value::Object(inner_map));
                    return Err(S::Error::custom(Value::Object(map).to_string()));
                }
            }
        }

        let mut map = serializer.serialize_map(Some(dict.len()))?;
        for (k, v) in dict.iter() {
            let key = k.cast::<PyString>().map_err(|e| S::Error::custom(e.to_string()))?
                .to_str().map_err(|e| S::Error::custom(e.to_string()))?;
            map.serialize_entry(key, &ValueSerializer {
                value: &v,
                inner: value_serializer,
                key: key.to_string(),
                ctx,
            })?;
        }
        map.end()
    }
}

pub mod dict_deserializer {
    use super::*;
    use crate::deserializer::Deserializer;
    use crate::types::LoadContext;
    use crate::utils::extract_error_value;

    #[inline]
    pub fn deserialize_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
        value_deserializer: &Deserializer,
        value_validator: Option<&Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDict>() {
            return Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(DICT_ERROR)));
        }
        let dict = value.cast::<PyDict>()?;
        let result = PyDict::new(ctx.py);

        for (k, v) in dict.iter() {
            let key_str: String = k.extract()?;
            let val = if v.is_none() {
                ctx.py.None()
            } else {
                match value_deserializer.deserialize_from_dict(&v, "value", None, ctx) {
                    Ok(val) => val,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        let wrapped = wrap_err_dict(ctx.py, &key_str, inner);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(ctx.py, field_name, wrapped),
                        ));
                    }
                }
            };
            if let Some(validator) = value_validator {
                if let Some(errors) = call_validator(ctx.py, validator, val.bind(ctx.py))? {
                    let wrapped_inner = wrap_err_dict(ctx.py, "value", errors);
                    let wrapped = wrap_err_dict(ctx.py, &key_str, wrapped_inner);
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        wrap_err_dict(ctx.py, field_name, wrapped),
                    ));
                }
            }
            result.set_item(k, val)?;
        }
        Ok(result.into_any().unbind())
    }
}
