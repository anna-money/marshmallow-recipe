use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};
use serde_json::Value;

use super::helpers::{field_error, json_field_error, err_dict_from_list, NESTED_ERROR};
use crate::cache::get_cached_types;
use crate::slots::set_slot_value_direct;
use crate::types::{SerializeContext, LoadContext};
use crate::utils::{call_validator, extract_error_args, pyany_to_json_value, wrap_err_dict};

pub struct DataclassSerializerSchema {
    pub cls: Py<PyAny>,
    pub fields: Vec<FieldSerializer>,
    pub field_lookup: HashMap<String, usize>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
}

impl Clone for DataclassSerializerSchema {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
        })
    }
}

pub struct FieldSerializer {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub serialized_name: Option<String>,
    pub serializer: crate::serializer::Serializer,
    pub optional: bool,
    pub slot_offset: Option<isize>,
    pub validator: Option<Py<PyAny>>,
}

impl std::fmt::Debug for FieldSerializer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FieldSerializer")
            .field("name", &self.name)
            .field("optional", &self.optional)
            .finish_non_exhaustive()
    }
}

impl Clone for FieldSerializer {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            name: self.name.clone(),
            name_interned: self.name_interned.clone_ref(py),
            serialized_name: self.serialized_name.clone(),
            serializer: self.serializer.clone(),
            optional: self.optional,
            slot_offset: self.slot_offset,
            validator: self.validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

pub struct DataclassDeserializerSchema {
    pub cls: Py<PyAny>,
    pub fields: Vec<FieldDeserializer>,
    pub field_lookup: HashMap<String, usize>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
}

impl Clone for DataclassDeserializerSchema {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
        })
    }
}

pub struct FieldDeserializer {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub serialized_name: Option<String>,
    pub deserializer: crate::deserializer::Deserializer,
    pub optional: bool,
    pub slot_offset: Option<isize>,
    pub default_value: Option<Py<PyAny>>,
    pub default_factory: Option<Py<PyAny>>,
    pub required_error: Option<String>,
    pub none_error: Option<String>,
    pub invalid_error: Option<String>,
    pub field_init: bool,
    pub validator: Option<Py<PyAny>>,
    pub item_validator: Option<Py<PyAny>>,
    pub value_validator: Option<Py<PyAny>>,
}

impl Clone for FieldDeserializer {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            name: self.name.clone(),
            name_interned: self.name_interned.clone_ref(py),
            serialized_name: self.serialized_name.clone(),
            deserializer: self.deserializer.clone(),
            optional: self.optional,
            slot_offset: self.slot_offset,
            default_value: self.default_value.as_ref().map(|v| v.clone_ref(py)),
            default_factory: self.default_factory.as_ref().map(|f| f.clone_ref(py)),
            required_error: self.required_error.clone(),
            none_error: self.none_error.clone(),
            invalid_error: self.invalid_error.clone(),
            field_init: self.field_init,
            validator: self.validator.as_ref().map(|v| v.clone_ref(py)),
            item_validator: self.item_validator.as_ref().map(|v| v.clone_ref(py)),
            value_validator: self.value_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

impl std::fmt::Debug for FieldDeserializer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FieldDeserializer")
            .field("name", &self.name)
            .field("optional", &self.optional)
            .finish_non_exhaustive()
    }
}

pub mod nested_serializer {
    use super::*;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        schema: &DataclassSerializerSchema,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance(schema.cls.bind(ctx.py))? {
            return Err(field_error(ctx.py, field_name, NESTED_ERROR));
        }
        serialize_dataclass(value, &schema.fields, ctx)
    }

    #[inline]
    pub fn serialize_to_json<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        schema: &DataclassSerializerSchema,
    ) -> Result<Value, String> {
        if !value.is_instance(schema.cls.bind(ctx.py)).map_err(|e| e.to_string())? {
            return Err(json_field_error(field_name, NESTED_ERROR));
        }
        serialize_dataclass_json(value, &schema.fields, ctx)
    }

    pub fn serialize_dataclass<'py>(
        obj: &Bound<'py, PyAny>,
        fields: &[FieldSerializer],
        ctx: &SerializeContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let ignore_none = ctx.none_value_handling.is_none_or(|s| s == "ignore");

        let cached = get_cached_types(ctx.py)?;
        let missing_sentinel = cached.missing_sentinel.bind(ctx.py);
        let result = PyDict::new(ctx.py);

        for field in fields {
            let py_value = match field.slot_offset {
                Some(offset) => match unsafe { crate::slots::get_slot_value_direct(ctx.py, obj, offset) } {
                    Some(value) => value,
                    None => obj.getattr(field.name.as_str())?,
                },
                None => obj.getattr(field.name.as_str())?,
            };

            if py_value.is(missing_sentinel) || (py_value.is_none() && ignore_none) {
                continue;
            }

            if let Some(ref validator) = field.validator {
                if let Some(errors) = call_validator(ctx.py, validator, &py_value)? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        err_dict_from_list(ctx.py, &field.name, errors),
                    ));
                }
            }

            let key = field.serialized_name.as_ref().unwrap_or(&field.name);

            let serialized_value = if py_value.is_none() {
                ctx.py.None()
            } else {
                field.serializer.serialize_to_dict(&py_value, &field.name, ctx)?
            };
            result.set_item(key.as_str(), serialized_value)?;
        }

        Ok(result.into_any().unbind())
    }

    pub fn serialize_dataclass_json<'py>(
        obj: &Bound<'py, PyAny>,
        fields: &[FieldSerializer],
        ctx: &SerializeContext<'_, 'py>,
    ) -> Result<Value, String> {
        let ignore_none = ctx.none_value_handling.is_none_or(|s| s == "ignore");

        let cached = get_cached_types(ctx.py).map_err(|e| e.to_string())?;
        let missing_sentinel = cached.missing_sentinel.bind(ctx.py);
        let mut result = serde_json::Map::new();

        for field in fields {
            let py_value = match field.slot_offset {
                Some(offset) => match unsafe { crate::slots::get_slot_value_direct(ctx.py, obj, offset) } {
                    Some(value) => value,
                    None => obj.getattr(field.name.as_str()).map_err(|e| e.to_string())?,
                },
                None => obj.getattr(field.name.as_str()).map_err(|e| e.to_string())?,
            };

            if py_value.is(missing_sentinel) || (py_value.is_none() && ignore_none) {
                continue;
            }

            if let Some(ref validator) = field.validator {
                if let Some(errors) = call_validator(ctx.py, validator, &py_value).map_err(|e| e.to_string())? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut map = serde_json::Map::new();
                    map.insert(field.name.clone(), errors_json);
                    return Err(Value::Object(map).to_string());
                }
            }

            let key = field.serialized_name.as_ref().unwrap_or(&field.name);

            let serialized_value = if py_value.is_none() {
                Value::Null
            } else {
                field.serializer.serialize_to_json(&py_value, &field.name, ctx)?
            };
            result.insert(key.clone(), serialized_value);
        }

        Ok(Value::Object(result))
    }

    struct FieldValueSerializer<'a, 'py> {
        value: &'a Bound<'py, PyAny>,
        serializer: &'a crate::serializer::Serializer,
        field_name: &'a str,
        ctx: &'a SerializeContext<'a, 'py>,
    }

    impl serde::Serialize for FieldValueSerializer<'_, '_> {
        fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
            self.serializer.serialize(self.value, self.field_name, self.ctx, serializer)
        }
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, '_>,
        schema: &DataclassSerializerSchema,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance(schema.cls.bind(ctx.py)).map_err(|e| S::Error::custom(e.to_string()))? {
            return Err(S::Error::custom(json_field_error(field_name, NESTED_ERROR)));
        }
        serialize_dataclass_streaming(value, &schema.fields, ctx, serializer)
    }

    pub fn serialize_dataclass_streaming<S: serde::Serializer>(
        obj: &Bound<'_, PyAny>,
        fields: &[FieldSerializer],
        ctx: &SerializeContext<'_, '_>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::{Error, SerializeMap};

        let ignore_none = ctx.none_value_handling.is_none_or(|s| s == "ignore");

        let cached = get_cached_types(ctx.py).map_err(|e| S::Error::custom(e.to_string()))?;
        let missing_sentinel = cached.missing_sentinel.bind(ctx.py);

        let mut map = serializer.serialize_map(None)?;

        for field in fields {
            let py_value = match field.slot_offset {
                Some(offset) => match unsafe { crate::slots::get_slot_value_direct(ctx.py, obj, offset) } {
                    Some(value) => value,
                    None => obj.getattr(field.name.as_str()).map_err(|e| S::Error::custom(e.to_string()))?,
                },
                None => obj.getattr(field.name.as_str()).map_err(|e| S::Error::custom(e.to_string()))?,
            };

            if py_value.is(missing_sentinel) || (py_value.is_none() && ignore_none) {
                continue;
            }

            if let Some(ref validator) = field.validator {
                if let Some(errors) = call_validator(ctx.py, validator, &py_value).map_err(|e| S::Error::custom(e.to_string()))? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut err_map = serde_json::Map::new();
                    err_map.insert(field.name.clone(), errors_json);
                    return Err(S::Error::custom(Value::Object(err_map).to_string()));
                }
            }

            let key = field.serialized_name.as_ref().unwrap_or(&field.name);

            if py_value.is_none() {
                map.serialize_entry(key.as_str(), &())?;
            } else {
                map.serialize_entry(key.as_str(), &FieldValueSerializer {
                    value: &py_value,
                    serializer: &field.serializer,
                    field_name: &field.name,
                    ctx,
                })?;
            }
        }

        map.end()
    }
}

pub mod nested_deserializer {
    use super::*;
    use crate::deserializer::Deserializer;

    #[inline]
    pub fn deserialize_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
        schema: &DataclassDeserializerSchema,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDict>() {
            return Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(NESTED_ERROR)));
        }
        deserialize_dataclass(value, schema, ctx).map_err(|e| {
            let inner = extract_error_args(ctx.py, &e);
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                wrap_err_dict(ctx.py, field_name, inner),
            )
        })
    }

    pub fn deserialize_dataclass<'py>(
        value: &Bound<'py, PyAny>,
        schema: &DataclassDeserializerSchema,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let dict = value.cast::<PyDict>().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a dict for dataclass")
        })?;
        let cls = schema.cls.bind(ctx.py);
        if schema.can_use_direct_slots {
            deserialize_dataclass_direct_slots(dict, cls, &schema.fields, &schema.field_lookup, ctx)
        } else {
            deserialize_dataclass_kwargs(dict, cls, &schema.fields, &schema.field_lookup, ctx)
        }
    }

    pub fn deserialize_dataclass_from_parts<'py>(
        value: &Bound<'py, PyAny>,
        cls: &Bound<'py, PyAny>,
        fields: &[FieldDeserializer],
        field_lookup: &HashMap<String, usize>,
        can_use_direct_slots: bool,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let dict = value.cast::<PyDict>().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a dict for dataclass")
        })?;
        if can_use_direct_slots {
            deserialize_dataclass_direct_slots(dict, cls, fields, field_lookup, ctx)
        } else {
            deserialize_dataclass_kwargs(dict, cls, fields, field_lookup, ctx)
        }
    }

    fn deserialize_dataclass_kwargs<'py>(
        dict: &Bound<'py, PyDict>,
        cls: &Bound<'py, PyAny>,
        fields: &[FieldDeserializer],
        field_lookup: &HashMap<String, usize>,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let kwargs = PyDict::new(ctx.py);
        let mut seen_fields = vec![false; fields.len()];

        for (key, value) in dict.iter() {
            let key_str: String = key.extract()?;
            if let Some(&idx) = field_lookup.get(&key_str) {
                let field = &fields[idx];
                seen_fields[idx] = true;
                if !field.field_init {
                    continue;
                }
                let deserialized = deserialize_field_value(&value, field, ctx)?;
                let validated = apply_post_load_and_validate(deserialized, field, ctx)?;
                kwargs.set_item(field.name_interned.bind(ctx.py), validated)?;
            }
        }

        for (idx, field) in fields.iter().enumerate() {
            if !seen_fields[idx] && field.field_init {
                if let Some(value) = get_default_value(field, ctx)? {
                    kwargs.set_item(field.name_interned.bind(ctx.py), value)?;
                } else {
                    let msg = field.required_error.as_deref().unwrap_or("Missing data for required field.");
                    return Err(field_error(ctx.py, &field.name, msg));
                }
            }
        }

        cls.call((), Some(&kwargs)).map(pyo3::Bound::unbind)
    }

    fn deserialize_dataclass_direct_slots<'py>(
        dict: &Bound<'py, PyDict>,
        cls: &Bound<'py, PyAny>,
        fields: &[FieldDeserializer],
        field_lookup: &HashMap<String, usize>,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let cached_types = get_cached_types(ctx.py)?;
        let object_type = cached_types.object_cls.bind(ctx.py);
        let instance = object_type.call_method1(cached_types.str_new.bind(ctx.py), (cls,))?;

        let mut field_values: Vec<Option<Py<PyAny>>> = (0..fields.len()).map(|_| None).collect();

        for (key, value) in dict.iter() {
            let key_str: String = key.extract()?;
            if let Some(&idx) = field_lookup.get(&key_str) {
                let field = &fields[idx];
                let deserialized = deserialize_field_value(&value, field, ctx)?;
                let validated = apply_post_load_and_validate(deserialized, field, ctx)?;
                field_values[idx] = Some(validated);
            }
        }

        for (idx, field) in fields.iter().enumerate() {
            let py_value = if let Some(value) = field_values[idx].take() {
                value
            } else if let Some(default) = get_default_value(field, ctx)? {
                default
            } else {
                let msg = field.required_error.as_deref().unwrap_or("Missing data for required field.");
                return Err(field_error(ctx.py, &field.name, msg));
            };

            if let Some(offset) = field.slot_offset {
                unsafe {
                    set_slot_value_direct(&instance, offset, py_value);
                }
            } else {
                instance.setattr(field.name_interned.bind(ctx.py), py_value)?;
            }
        }

        Ok(instance.unbind())
    }

    pub fn deserialize_field_value<'py>(
        value: &Bound<'py, PyAny>,
        field: &FieldDeserializer,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if matches!(field.deserializer, Deserializer::Any) {
            return Ok(value.clone().unbind());
        }

        if value.is_none() {
            if !field.optional {
                let msg = field.none_error.as_deref().unwrap_or("Field may not be null.");
                return Err(field_error(ctx.py, &field.name, msg));
            }
            return Ok(ctx.py.None());
        }

        field.deserializer.deserialize_from_dict(value, &field.name, field.invalid_error.as_deref(), ctx)
    }

    fn get_default_value(field: &FieldDeserializer, ctx: &LoadContext<'_, '_>) -> PyResult<Option<Py<PyAny>>> {
        if let Some(ref factory) = field.default_factory {
            return Ok(Some(factory.call0(ctx.py)?));
        }
        if let Some(ref value) = field.default_value {
            return Ok(Some(value.clone_ref(ctx.py)));
        }
        Ok(field.optional.then(|| ctx.py.None()))
    }

    fn apply_post_load_and_validate(
        value: Py<PyAny>,
        field: &FieldDeserializer,
        ctx: &LoadContext<'_, '_>,
    ) -> PyResult<Py<PyAny>> {
        let mut result = value;

        if let Some(pl) = ctx.post_loads {
            if let Ok(Some(post_load_fn)) = pl.get_item(&field.name) {
                if !post_load_fn.is_none() {
                    result = post_load_fn.call1((result,))?.unbind();
                }
            }
        }

        if let Some(ref validator) = field.validator {
            if let Some(errors) = call_validator(ctx.py, validator, result.bind(ctx.py))? {
                let dict = PyDict::new(ctx.py);
                dict.set_item(&field.name, errors).unwrap();
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(dict.into_any().unbind()));
            }
        }

        Ok(result)
    }
}
