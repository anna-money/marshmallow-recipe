use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyFrozenSet, PyList, PySet, PyTuple};

use super::helpers::{field_error, json_field_error, LIST_ERROR, SET_ERROR, FROZENSET_ERROR, TUPLE_ERROR};
use crate::types::SerializeContext;
use crate::utils::{call_validator, format_item_errors_dict, wrap_err_dict, wrap_err_dict_idx};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CollectionKind {
    List,
    Set,
    FrozenSet,
    Tuple,
}

impl CollectionKind {
    pub const fn error_msg(self) -> &'static str {
        match self {
            Self::List => LIST_ERROR,
            Self::Set => SET_ERROR,
            Self::FrozenSet => FROZENSET_ERROR,
            Self::Tuple => TUPLE_ERROR,
        }
    }

    pub fn is_valid_type(self, value: &Bound<'_, PyAny>) -> bool {
        match self {
            Self::List => value.is_instance_of::<PyList>(),
            Self::Set => value.is_instance_of::<PySet>(),
            Self::FrozenSet => value.is_instance_of::<PyFrozenSet>(),
            Self::Tuple => value.is_instance_of::<PyTuple>(),
        }
    }
}

pub mod collection_serializer {
    use super::*;
    use crate::serializer::Serializer;
    use crate::utils::pyany_to_json_value;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        kind: CollectionKind,
        item_serializer: &Serializer,
        item_validator: Option<&Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let err_msg = kind.error_msg();

        if !kind.is_valid_type(value) {
            return Err(field_error(ctx.py, field_name, err_msg));
        }

        let iter = value.try_iter()?;
        let result = PyList::empty(ctx.py);
        let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;

        for (idx, item_result) in iter.enumerate() {
            let item = item_result?;
            if let Some(validator) = item_validator {
                if let Some(errors) = call_validator(ctx.py, validator, &item)? {
                    item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                }
            }
            let serialized = serialize_item(item_serializer, &item, &idx.to_string(), ctx)?;
            result.append(serialized)?;
        }

        if let Some(ref errs) = item_errors {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                wrap_err_dict(ctx.py, field_name, format_item_errors_dict(ctx.py, errs)),
            ));
        }

        Ok(result.into_any().unbind())
    }

    fn serialize_item<'py>(
        item_serializer: &Serializer,
        value: &Bound<'py, PyAny>,
        item_name: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if value.is_none() {
            return Ok(ctx.py.None());
        }
        item_serializer.serialize_to_dict(value, item_name, ctx)
    }

    #[inline]
    pub fn serialize_to_json<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
        kind: CollectionKind,
        item_serializer: &Serializer,
        item_validator: Option<&Py<PyAny>>,
    ) -> Result<serde_json::Value, String> {
        let err_msg = kind.error_msg();

        if !kind.is_valid_type(value) {
            return Err(json_field_error(field_name, err_msg));
        }

        let iter = value.try_iter().map_err(|e| e.to_string())?;

        if let Some(validator) = item_validator {
            let mut validated_items = Vec::new();
            for (idx, item_result) in iter.enumerate() {
                let item = item_result.map_err(|e| e.to_string())?;
                if let Some(errors) = call_validator(ctx.py, validator, &item).map_err(|e| e.to_string())? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut inner_map = serde_json::Map::new();
                    inner_map.insert(idx.to_string(), errors_json);
                    let mut map = serde_json::Map::new();
                    map.insert(field_name.to_string(), serde_json::Value::Object(inner_map));
                    return Err(serde_json::Value::Object(map).to_string());
                }
                validated_items.push(item);
            }
            let mut result = Vec::with_capacity(validated_items.len());
            for (idx, item) in validated_items.iter().enumerate() {
                let serialized = serialize_item_json(item_serializer, item, &idx.to_string(), ctx)?;
                result.push(serialized);
            }
            Ok(serde_json::Value::Array(result))
        } else {
            let mut result = Vec::new();
            for (idx, item_result) in iter.enumerate() {
                let item = item_result.map_err(|e| e.to_string())?;
                let serialized = serialize_item_json(item_serializer, &item, &idx.to_string(), ctx)?;
                result.push(serialized);
            }
            Ok(serde_json::Value::Array(result))
        }
    }

    fn serialize_item_json<'py>(
        item_serializer: &Serializer,
        value: &Bound<'py, PyAny>,
        item_name: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> Result<serde_json::Value, String> {
        if value.is_none() {
            return Ok(serde_json::Value::Null);
        }
        item_serializer.serialize_to_json(value, item_name, ctx)
    }

    struct ItemSerializer<'a, 'py> {
        value: &'a Bound<'py, PyAny>,
        inner: &'a Serializer,
        name: String,
        ctx: &'a SerializeContext<'a, 'py>,
    }

    impl serde::Serialize for ItemSerializer<'_, '_> {
        fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
            if self.value.is_none() {
                return serializer.serialize_none();
            }
            self.inner.serialize(self.value, &self.name, self.ctx, serializer)
        }
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, '_>,
        kind: CollectionKind,
        item_serializer: &Serializer,
        item_validator: Option<&Py<PyAny>>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::{Error, SerializeSeq};

        let err_msg = kind.error_msg();

        if !kind.is_valid_type(value) {
            return Err(S::Error::custom(json_field_error(field_name, err_msg)));
        }

        let iter = value.try_iter().map_err(|e| S::Error::custom(e.to_string()))?;
        let len_hint = value.len().unwrap_or(0);

        if let Some(validator) = item_validator {
            let mut validated_items = Vec::with_capacity(len_hint);
            for (idx, item_result) in iter.enumerate() {
                let item = item_result.map_err(|e| S::Error::custom(e.to_string()))?;
                if let Some(errors) = call_validator(ctx.py, validator, &item).map_err(|e| S::Error::custom(e.to_string()))? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut inner_map = serde_json::Map::new();
                    inner_map.insert(idx.to_string(), errors_json);
                    let mut map = serde_json::Map::new();
                    map.insert(field_name.to_string(), serde_json::Value::Object(inner_map));
                    return Err(S::Error::custom(serde_json::Value::Object(map).to_string()));
                }
                validated_items.push(item);
            }
            let mut seq = serializer.serialize_seq(Some(validated_items.len()))?;
            for (idx, item) in validated_items.iter().enumerate() {
                seq.serialize_element(&ItemSerializer {
                    value: item,
                    inner: item_serializer,
                    name: idx.to_string(),
                    ctx,
                })?;
            }
            seq.end()
        } else {
            let items: Vec<_> = iter
                .enumerate()
                .map(|(idx, item_result)| item_result.map(|item| (idx, item)))
                .collect::<Result<_, _>>()
                .map_err(|e| S::Error::custom(e.to_string()))?;

            let mut seq = serializer.serialize_seq(Some(items.len()))?;
            for (idx, item) in &items {
                seq.serialize_element(&ItemSerializer {
                    value: item,
                    inner: item_serializer,
                    name: idx.to_string(),
                    ctx,
                })?;
            }
            seq.end()
        }
    }
}

pub mod collection_deserializer {
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
        kind: CollectionKind,
        item_deserializer: &Deserializer,
        item_validator: Option<&Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let err_msg = kind.error_msg();

        if kind == CollectionKind::List {
            if !value.is_instance_of::<PyList>() {
                return Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(err_msg)));
            }
        } else {
            let is_valid_iterable = value.is_instance_of::<PyList>()
                || value.is_instance_of::<PyTuple>()
                || value.is_instance_of::<PySet>()
                || value.is_instance_of::<PyFrozenSet>();
            if !is_valid_iterable {
                return Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(err_msg)));
            }
        }
        let iter = value.try_iter()?;

        let items = PyList::empty(ctx.py);
        for (idx, item_result) in iter.enumerate() {
            let item = item_result?;
            match deserialize_item(item_deserializer, &item, ctx) {
                Ok(v) => {
                    if let Some(validator) = item_validator {
                        if let Some(errors) = call_validator(ctx.py, validator, v.bind(ctx.py))? {
                            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                wrap_err_dict(ctx.py, field_name, wrap_err_dict_idx(ctx.py, idx, errors)),
                            ));
                        }
                    }
                    items.append(v)?;
                }
                Err(e) => {
                    let inner = extract_error_value(ctx.py, &e);
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        wrap_err_dict(ctx.py, field_name, wrap_err_dict_idx(ctx.py, idx, inner)),
                    ));
                }
            }
        }

        match kind {
            CollectionKind::List => Ok(items.into_any().unbind()),
            CollectionKind::Set => Ok(PySet::new(ctx.py, items.iter())?.into_any().unbind()),
            CollectionKind::FrozenSet => Ok(PyFrozenSet::new(ctx.py, items.iter())?.into_any().unbind()),
            CollectionKind::Tuple => Ok(PyTuple::new(ctx.py, items.iter())?.into_any().unbind()),
        }
    }

    fn deserialize_item<'py>(
        item_deserializer: &Deserializer,
        value: &Bound<'py, PyAny>,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if value.is_none() {
            return Ok(ctx.py.None());
        }
        item_deserializer.deserialize_from_dict(value, "", None, ctx)
    }
}
