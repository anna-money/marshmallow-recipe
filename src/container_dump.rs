use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::container::{DataclassContainer, DataclassRegistry, FieldContainer, TypeContainer};
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
use crate::fields::{
    any, bool_literal, bool_type, collection, date, datetime, decimal, dict, float_type, int_enum,
    int_literal, int_type, str_enum, str_literal, str_type, time, union, uuid,
};
use crate::utils::{call_validator, new_presized_list};

#[allow(clippy::cast_sign_loss, clippy::unused_self)]
impl FieldContainer {
    pub fn dump_to_py(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        if value.is_none() {
            return Ok(value.py().None());
        }

        let common = self.common();
        match self {
            Self::Str {
                strip_whitespaces, ..
            } => str_type::dump_to_py(
                value,
                *strip_whitespaces,
                common.optional,
                &common.invalid_error,
            ),
            Self::Int { .. } => int_type::dump_to_py(value, &common.invalid_error),
            Self::Float { .. } => float_type::dump_to_py(value, &common.invalid_error),
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
            Self::IntEnum {
                common,
                dumper_data,
                ..
            } => int_enum::dump_to_py(value, &dumper_data.enum_cls, &common.invalid_error),
            Self::StrEnum {
                common,
                dumper_data,
                ..
            } => str_enum::dump_to_py(value, &dumper_data.enum_cls, &common.invalid_error),
            Self::StrLiteral { common, data } => {
                str_literal::dump_to_py(value, data, &common.invalid_error)
            }
            Self::IntLiteral { common, data } => {
                int_literal::dump_to_py(value, data, &common.invalid_error)
            }
            Self::BoolLiteral { common, data } => {
                bool_literal::dump_to_py(value, data, &common.invalid_error)
            }
            Self::Any { .. } => any::dump_to_py(value),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => collection::dump_to_py(
                registry,
                value,
                *kind,
                item,
                item_validator.as_ref(),
                &common.invalid_error,
            ),
            Self::Dict {
                value: value_schema,
                value_validator,
                ..
            } => dict::dump_to_py(
                registry,
                value,
                value_schema,
                value_validator.as_ref(),
                &common.invalid_error,
            ),
            Self::Nested {
                dataclass_index, ..
            } => registry.get(*dataclass_index).dump_to_py(registry, value),
            Self::Union { variants, .. } => union::dump_to_py(registry, value, variants),
        }
    }
}

impl DataclassContainer {
    pub fn dump_to_py(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
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

        let missing_sentinel = crate::utils::get_missing_sentinel(py)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        let result = PyDict::new(py);
        let mut errors: Option<Bound<'_, PyDict>> = None;

        for dc_field in &self.fields {
            let common = dc_field.field.common();

            let py_value = match dc_field.slot_offset {
                Some(offset) => {
                    match unsafe { crate::slots::get_slot_value_direct(py, value, offset) } {
                        Some(v) => v,
                        None => value
                            .getattr(dc_field.name_interned.bind(py))
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))?,
                    }
                }
                None => value
                    .getattr(dc_field.name_interned.bind(py))
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?,
            };

            if py_value.is(missing_sentinel.as_any()) || (py_value.is_none() && self.ignore_none) {
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
                result
                    .set_item(dc_field.data_key_interned.bind(py), py.None())
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            } else {
                match dc_field.field.dump_to_py(registry, &py_value) {
                    Ok(dumped) => {
                        if dumped.is_none(py) && self.ignore_none {
                            continue;
                        }
                        result
                            .set_item(dc_field.data_key_interned.bind(py), dumped)
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    }
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                    }
                }
            }
        }

        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }

        Ok(result.into_any().unbind())
    }
}

impl TypeContainer {
    pub fn dump_to_py(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let py = value.py();

        match self {
            Self::Dataclass(idx) => registry.get(*idx).dump_to_py(registry, value),
            Self::Primitive(p) => {
                if value.is_none() {
                    return Ok(py.None());
                }
                p.field.dump_to_py(registry, value)
            }
            Self::List { item } => {
                let list = value.cast::<PyList>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a list").clone().unbind())
                })?;
                let result = new_presized_list(py, list.len());
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (idx, v) in list.iter().enumerate() {
                    match item.dump_to_py(registry, &v) {
                        Ok(dumped) => unsafe {
                            pyo3::ffi::PyList_SET_ITEM(
                                result.as_ptr(),
                                idx.cast_signed(),
                                dumped.into_ptr(),
                            );
                        },
                        Err(ref e) => accumulate_error(py, &mut errors, idx, e),
                    }
                }

                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }

                Ok(result.into_any().unbind())
            }
            Self::Dict {
                value: value_container,
            } => {
                let dict = value.cast::<PyDict>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a dict").clone().unbind())
                })?;
                let result = PyDict::new(py);
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (k, v) in dict.iter() {
                    match value_container.dump_to_py(registry, &v) {
                        Ok(dumped) => {
                            result
                                .set_item(k, dumped)
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                        }
                        Err(ref e) => {
                            let key_str = k.str().map(|s| s.to_string()).unwrap_or_default();
                            accumulate_error(py, &mut errors, key_str, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }

                Ok(result.into_any().unbind())
            }
            Self::Optional { inner } => {
                if value.is_none() {
                    Ok(py.None())
                } else {
                    inner.dump_to_py(registry, value)
                }
            }
            Self::Set { item } | Self::FrozenSet { item } | Self::Tuple { item } => {
                let iter = value.try_iter().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected an iterable").clone().unbind())
                })?;
                let (size_hint, _) = iter.size_hint();
                let mut items = Vec::with_capacity(size_hint);
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (idx, item_result) in iter.enumerate() {
                    let v =
                        item_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    match item.dump_to_py(registry, &v) {
                        Ok(dumped) => items.push(dumped),
                        Err(ref e) => accumulate_error(py, &mut errors, idx, e),
                    }
                }

                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }

                PyList::new(py, items)
                    .map(|l| l.into_any().unbind())
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            }
            Self::Union { variants } => {
                for variant in variants {
                    if let Ok(result) = variant.dump_to_py(registry, value) {
                        return Ok(result);
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
