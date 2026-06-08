use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};

use crate::container::{DataclassContainer, DataclassRegistry, FieldContainer, TypeContainer};
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
use crate::fields::collection::CollectionKind;
use crate::fields::length::{LengthBound, validate_length};
use crate::fields::{
    any, bool_literal, bool_type, bytes, date, datetime, decimal, float_type, int_enum,
    int_literal, int_type, str_enum, str_literal, str_type, time, uuid,
};
use crate::json::sink::{DumpSink, PyDictSink, wrap_value_error};
use crate::slots::get_slot_value_direct;
use crate::utils::{call_validator, get_missing_sentinel};

#[allow(clippy::too_many_arguments)]
fn dump_collection<'py, S: DumpSink<'py>>(
    registry: &DataclassRegistry,
    value: &Bound<'py, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
    min_length: Option<&LengthBound>,
    max_length: Option<&LengthBound>,
    sink: &mut S,
    key: Option<&str>,
) -> Result<(), SerializationError> {
    let py = value.py();

    if !kind.is_valid_type(value) {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let size = value
        .len()
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    validate_length(py, size, min_length, max_length)?;

    sink.open_array(key, |s| {
        let mut errors: Option<Bound<'_, PyDict>> = None;
        let iter = value
            .try_iter()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        for (idx, item_result) in iter.enumerate() {
            let v = item_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            if let Some(validator) = item_validator
                && let Ok(Some(err_list)) = call_validator(py, validator, &v)
            {
                let e = pyerrors_to_serialization_error(py, &err_list);
                accumulate_error(py, &mut errors, idx, &e);
                continue;
            }
            match item.dump(registry, &v, s, None) {
                Ok(true) => {}
                Ok(false) => s.null(None)?,
                Err(ref e) => accumulate_error(py, &mut errors, idx, e),
            }
        }
        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }
        Ok(())
    })
}

fn dump_dict<'py, S: DumpSink<'py>>(
    registry: &DataclassRegistry,
    value: &Bound<'py, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
    sink: &mut S,
    key: Option<&str>,
) -> Result<(), SerializationError> {
    let py = value.py();
    let dict = value
        .cast::<PyDict>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;

    sink.open_object(key, |s| {
        let mut errors: Option<Bound<'_, PyDict>> = None;
        for (k, v) in dict.iter() {
            let key_obj = k.cast::<PyString>().map_err(|_| {
                SerializationError::Single(
                    intern!(py, "Dict key must be a string").clone().unbind(),
                )
            })?;
            let key_str = key_obj
                .to_str()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

            if let Some(validator) = value_validator
                && let Ok(Some(err_list)) = call_validator(py, validator, &v)
            {
                let e = pyerrors_to_serialization_error(py, &err_list);
                accumulate_error(py, &mut errors, key_str, &e);
                continue;
            }

            match value_schema.dump(registry, &v, s, Some(key_str)) {
                Ok(true) => {}
                Ok(false) => s.null(Some(key_str))?,
                Err(ref e) => {
                    accumulate_error(py, &mut errors, key_str, &wrap_value_error(py, e));
                }
            }
        }
        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }
        Ok(())
    })
}

impl FieldContainer {
    pub fn dump<'py, S: DumpSink<'py>>(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'py, PyAny>,
        sink: &mut S,
        key: Option<&str>,
    ) -> Result<bool, SerializationError> {
        let py = value.py();
        if value.is_none() {
            return Ok(false);
        }

        match self {
            Self::Any { .. } => {
                let v = any::dump_to_py(value)?;
                sink.pyobject(key, v.bind(py))?;
                Ok(true)
            }
            Self::Collection {
                common,
                kind,
                item,
                item_validator,
                min_length,
                max_length,
            } => {
                dump_collection(
                    registry,
                    value,
                    *kind,
                    item,
                    item_validator.as_ref(),
                    &common.invalid_error,
                    min_length.as_ref(),
                    max_length.as_ref(),
                    sink,
                    key,
                )?;
                Ok(true)
            }
            Self::Dict {
                common,
                value: value_schema,
                value_validator,
            } => {
                dump_dict(
                    registry,
                    value,
                    value_schema,
                    value_validator.as_ref(),
                    &common.invalid_error,
                    sink,
                    key,
                )?;
                Ok(true)
            }
            Self::Nested {
                dataclass_index, ..
            } => {
                registry
                    .get(*dataclass_index)
                    .dump(registry, value, sink, key)?;
                Ok(true)
            }
            Self::Union { variants, .. } => {
                for variant in variants {
                    let mut tmp = PyDictSink::new(py);
                    match variant.dump(registry, value, &mut tmp, None) {
                        Ok(true) => {
                            let materialized = tmp.finish();
                            sink.pyobject(key, materialized.bind(py))?;
                            return Ok(true);
                        }
                        Ok(false) => return Ok(false),
                        Err(_) => {}
                    }
                }
                Err(SerializationError::Single(
                    intern!(py, "Value does not match any union variant")
                        .clone()
                        .unbind(),
                ))
            }
            _ => {
                let dumped = self.dump_leaf(value)?;
                if dumped.is_none(py) {
                    Ok(false)
                } else {
                    sink.leaf(key, dumped.bind(py))?;
                    Ok(true)
                }
            }
        }
    }

    fn dump_leaf(&self, value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, SerializationError> {
        let common = self.common();
        match self {
            Self::Str {
                strip_whitespaces,
                min_length,
                max_length,
                ..
            } => str_type::dump_to_py(
                value,
                *strip_whitespaces,
                common.optional,
                &common.invalid_error,
                min_length.as_ref(),
                max_length.as_ref(),
            ),
            Self::Int {
                gt, gte, lt, lte, ..
            } => int_type::dump_to_py(
                value,
                &common.invalid_error,
                gt.as_ref(),
                gte.as_ref(),
                lt.as_ref(),
                lte.as_ref(),
            ),
            Self::Float {
                gt, gte, lt, lte, ..
            } => float_type::dump_to_py(
                value,
                &common.invalid_error,
                gt.as_ref(),
                gte.as_ref(),
                lt.as_ref(),
                lte.as_ref(),
            ),
            Self::Bool { .. } => bool_type::dump_to_py(value, &common.invalid_error),
            Self::Decimal {
                decimal_places,
                rounding,
                gt,
                gte,
                lt,
                lte,
                ..
            } => decimal::dump_to_py(
                value,
                *decimal_places,
                rounding.as_ref(),
                &common.invalid_error,
                gt.as_ref(),
                gte.as_ref(),
                lt.as_ref(),
                lte.as_ref(),
            ),
            Self::Date { .. } => date::dump_to_py(value, &common.invalid_error),
            Self::Time { .. } => time::dump_to_py(value, &common.invalid_error),
            Self::DateTime { format, .. } => {
                datetime::dump_to_py(value, format, &common.invalid_error)
            }
            Self::Uuid { .. } => uuid::dump_to_py(value, &common.invalid_error),
            Self::Bytes { .. } => bytes::dump_to_py(value, &common.invalid_error),
            Self::IntEnum {
                common,
                enum_values,
                enum_cls,
            } => int_enum::dump_to_py(value, enum_values, enum_cls, &common.invalid_error),
            Self::StrEnum {
                common,
                enum_values,
                enum_cls,
            } => str_enum::dump_to_py(value, enum_values, enum_cls, &common.invalid_error),
            Self::StrLiteral { common, values } => {
                str_literal::dump_to_py(value, values, &common.invalid_error)
            }
            Self::IntLiteral { common, values } => {
                int_literal::dump_to_py(value, values, &common.invalid_error)
            }
            Self::BoolLiteral { common, values } => {
                bool_literal::dump_to_py(value, values, &common.invalid_error)
            }
            _ => unreachable!("dump_leaf called on a non-leaf field"),
        }
    }
}

impl DataclassContainer {
    pub fn dump<'py, S: DumpSink<'py>>(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'py, PyAny>,
        sink: &mut S,
        key: Option<&str>,
    ) -> Result<(), SerializationError> {
        let py = value.py();

        if !value.is_instance(self.cls.bind(py)).unwrap_or(false) {
            return Err(SerializationError::Single(
                intern!(
                    py,
                    "Invalid nested object type. Expected instance of dataclass."
                )
                .clone()
                .unbind(),
            ));
        }

        let missing_sentinel =
            get_missing_sentinel(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        sink.open_object(key, |s| {
            let mut errors: Option<Bound<'_, PyDict>> = None;

            for dc_field in &self.fields {
                if !dc_field.field_init {
                    continue;
                }

                let common = dc_field.field.common();

                let py_value = match dc_field.slot_offset {
                    Some(offset) => match unsafe { get_slot_value_direct(py, value, offset) } {
                        Some(v) => v,
                        None => value
                            .getattr(dc_field.name_interned.bind(py))
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))?,
                    },
                    None => value
                        .getattr(dc_field.name_interned.bind(py))
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?,
                };

                if py_value.is(missing_sentinel.as_any())
                    || (py_value.is_none() && self.ignore_none)
                {
                    continue;
                }

                if let Some(ref validator) = common.validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, &py_value)
                {
                    let e = pyerrors_to_serialization_error(py, &err_list);
                    accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), &e);
                    continue;
                }

                if py_value.is_none() {
                    s.null(Some(&dc_field.data_key))?;
                    continue;
                }

                match dc_field
                    .field
                    .dump(registry, &py_value, s, Some(&dc_field.data_key))
                {
                    Ok(true) => {}
                    Ok(false) => {
                        if !self.ignore_none {
                            s.null(Some(&dc_field.data_key))?;
                        }
                    }
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                    }
                }
            }

            if let Some(errors) = errors {
                return Err(SerializationError::Dict(errors.unbind()));
            }
            Ok(())
        })
    }
}

impl TypeContainer {
    pub fn dump<'py, S: DumpSink<'py>>(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'py, PyAny>,
        sink: &mut S,
        key: Option<&str>,
    ) -> Result<(), SerializationError> {
        let py = value.py();

        match self {
            Self::Dataclass(idx) => registry.get(*idx).dump(registry, value, sink, key),
            Self::Primitive(p) => {
                if value.is_none() {
                    sink.null(key)
                } else if p.field.dump(registry, value, sink, key)? {
                    Ok(())
                } else {
                    sink.null(key)
                }
            }
            Self::List { item } => {
                let list = value.cast::<PyList>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a list").clone().unbind())
                })?;
                sink.open_array(key, |s| {
                    let mut errors: Option<Bound<'_, PyDict>> = None;
                    for (idx, v) in list.iter().enumerate() {
                        if let Err(ref e) = item.dump(registry, &v, s, None) {
                            accumulate_error(py, &mut errors, idx, e);
                        }
                    }
                    if let Some(errors) = errors {
                        return Err(SerializationError::Dict(errors.unbind()));
                    }
                    Ok(())
                })
            }
            Self::Dict { value: vc } => {
                let dict = value.cast::<PyDict>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a dict").clone().unbind())
                })?;
                sink.open_object(key, |s| {
                    let mut errors: Option<Bound<'_, PyDict>> = None;
                    for (k, v) in dict.iter() {
                        let key_owned;
                        let key_str = if let Ok(key_obj) = k.cast::<PyString>() {
                            key_obj
                                .to_str()
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))?
                        } else {
                            key_owned = k
                                .str()
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                            key_owned
                                .to_str()
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))?
                        };
                        if let Err(ref e) = vc.dump(registry, &v, s, Some(key_str)) {
                            accumulate_error(py, &mut errors, key_str, e);
                        }
                    }
                    if let Some(errors) = errors {
                        return Err(SerializationError::Dict(errors.unbind()));
                    }
                    Ok(())
                })
            }
            Self::Optional { inner } => {
                if value.is_none() {
                    sink.null(key)
                } else {
                    inner.dump(registry, value, sink, key)
                }
            }
            Self::Set { item } | Self::FrozenSet { item } | Self::Tuple { item } => sink
                .open_array(key, |s| {
                    let iter = value.try_iter().map_err(|_| {
                        SerializationError::Single(
                            intern!(py, "Expected an iterable").clone().unbind(),
                        )
                    })?;
                    let mut errors: Option<Bound<'_, PyDict>> = None;
                    for (idx, item_result) in iter.enumerate() {
                        let v = item_result
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                        if let Err(ref e) = item.dump(registry, &v, s, None) {
                            accumulate_error(py, &mut errors, idx, e);
                        }
                    }
                    if let Some(errors) = errors {
                        return Err(SerializationError::Dict(errors.unbind()));
                    }
                    Ok(())
                }),
            Self::Union { variants } => {
                for variant in variants {
                    let mut tmp = PyDictSink::new(py);
                    if variant.dump(registry, value, &mut tmp, None).is_ok() {
                        let materialized = tmp.finish();
                        return sink.pyobject(key, materialized.bind(py));
                    }
                }
                Err(SerializationError::Single(
                    intern!(py, "Value does not match any union variant")
                        .clone()
                        .unbind(),
                ))
            }
        }
    }
}
