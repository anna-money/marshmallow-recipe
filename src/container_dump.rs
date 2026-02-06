use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::container::{DataclassContainer, FieldContainer, TypeContainer};
use crate::error::DumpError;
use crate::error_convert::pyerrors_to_dump_error;
use crate::fields::{
    any, bool_type, collection, date, datetime, decimal, dict, float_type, int_enum, int_type,
    str_enum, str_type, time, union, uuid,
};
use crate::utils::{call_validator, new_presized_dict};

#[allow(clippy::cast_sign_loss, clippy::unused_self)]
impl FieldContainer {
    pub fn dump_to_py(
        &self,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, DumpError> {
        if value.is_none() {
            return Ok(value.py().None());
        }

        match self {
            Self::Str {
                strip_whitespaces, ..
            } => str_type::dump_to_py(value, *strip_whitespaces),
            Self::Int { .. } => int_type::dump_to_py(value),
            Self::Float { .. } => float_type::dump_to_py(value),
            Self::Bool { .. } => bool_type::dump_to_py(value),
            Self::Decimal { decimal_places, rounding, .. } => {
                decimal::dump_to_py(value, *decimal_places, rounding.as_ref())
            }
            Self::Date { .. } => date::dump_to_py(value),
            Self::Time { .. } => time::dump_to_py(value),
            Self::DateTime { format, .. } => datetime::dump_to_py(value, format),
            Self::Uuid { .. } => uuid::dump_to_py(value),
            Self::StrEnum { dumper_data, .. } => str_enum::dump_to_py(value, dumper_data),
            Self::IntEnum { dumper_data, .. } => int_enum::dump_to_py(value, dumper_data),
            Self::Any { .. } => any::dump_to_py(value),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => collection::dump_to_py(value, *kind, item, item_validator.as_ref()),
            Self::Dict {
                value: value_schema,
                value_validator,
                ..
            } => dict::dump_to_py(value, value_schema, value_validator.as_ref()),
            Self::Nested { container, .. } => container.dump_to_py(value),
            Self::Union { variants, .. } => union::dump_to_py(value, variants),
        }
    }
}


impl DataclassContainer {
    pub fn dump_to_py(
        &self,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, DumpError> {
        let py = value.py();

        if !value.is_instance(self.cls.bind(py)).unwrap_or(false) {
            return Err(DumpError::simple(
                "Invalid nested object type. Expected instance of dataclass.",
            ));
        }

        let missing_sentinel = crate::utils::get_missing_sentinel(py)
            .map_err(|e| DumpError::simple(&e.to_string()))?;

        let result = new_presized_dict(py, self.fields.len());
        let mut errors: Option<HashMap<String, DumpError>> = None;

        for dc_field in &self.fields {
            let common = dc_field.field.common();

            let py_value = match dc_field.slot_offset {
                Some(offset) => {
                    match unsafe { crate::slots::get_slot_value_direct(py, value, offset) } {
                        Some(v) => v,
                        None => value
                            .getattr(dc_field.name.as_str())
                            .map_err(|e| DumpError::simple(&e.to_string()))?,
                    }
                }
                None => value
                    .getattr(dc_field.name.as_str())
                    .map_err(|e| DumpError::simple(&e.to_string()))?,
            };

            if py_value.is(missing_sentinel.as_any()) || (py_value.is_none() && self.ignore_none) {
                continue;
            }

            if let Some(ref validator) = common.validator
                && let Ok(Some(err_list)) = call_validator(py, validator, &py_value)
            {
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(dc_field.name.clone(), pyerrors_to_dump_error(py, &err_list));
                continue;
            }

            let key_interned = dc_field
                .data_key_interned
                .as_ref()
                .unwrap_or(&dc_field.name_interned);

            if py_value.is_none() {
                result
                    .set_item(key_interned.bind(py), py.None())
                    .map_err(|e| DumpError::simple(&e.to_string()))?;
            } else {
                match dc_field.field.dump_to_py(&py_value) {
                    Ok(dumped) => {
                        result
                            .set_item(key_interned.bind(py), dumped)
                            .map_err(|e| DumpError::simple(&e.to_string()))?;
                    }
                    Err(e) => {
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(dc_field.name.clone(), e);
                    }
                }
            }
        }

        if let Some(errors) = errors {
            return Err(DumpError::Multiple(errors));
        }

        Ok(result.into_any().unbind())
    }
}

impl TypeContainer {
    pub fn dump_to_py(
        &self,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, DumpError> {
        let py = value.py();

        match self {
            Self::Dataclass(dc) => dc.dump_to_py(value),
            Self::Primitive(p) => {
                if value.is_none() {
                    return Ok(py.None());
                }
                p.field.dump_to_py(value)
            }
            Self::List { item } => {
                let list = value
                    .cast::<PyList>()
                    .map_err(|_| DumpError::simple("Expected a list"))?;
                let result = PyList::empty(py);
                let mut errors: Option<HashMap<usize, DumpError>> = None;

                for (idx, v) in list.iter().enumerate() {
                    match item.dump_to_py(&v) {
                        Ok(dumped) => {
                            result
                                .append(dumped)
                                .map_err(|e| DumpError::simple(&e.to_string()))?;
                        }
                        Err(e) => {
                            errors.get_or_insert_with(HashMap::new).insert(idx, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(DumpError::IndexMultiple(errors));
                }

                Ok(result.into_any().unbind())
            }
            Self::Dict { value: value_container } => {
                let dict = value
                    .cast::<PyDict>()
                    .map_err(|_| DumpError::simple("Expected a dict"))?;
                let result = new_presized_dict(py, dict.len());
                let mut errors: Option<HashMap<String, DumpError>> = None;

                for (k, v) in dict.iter() {
                    match value_container.dump_to_py(&v) {
                        Ok(dumped) => {
                            result
                                .set_item(k, dumped)
                                .map_err(|e| DumpError::simple(&e.to_string()))?;
                        }
                        Err(e) => {
                            let key_str = k.str().map(|s| s.to_string()).unwrap_or_default();
                            errors.get_or_insert_with(HashMap::new).insert(key_str, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(DumpError::Multiple(errors));
                }

                Ok(result.into_any().unbind())
            }
            Self::Optional { inner } => {
                if value.is_none() {
                    Ok(py.None())
                } else {
                    inner.dump_to_py(value)
                }
            }
            Self::Set { item } | Self::FrozenSet { item } | Self::Tuple { item } => {
                let iter = value
                    .try_iter()
                    .map_err(|_| DumpError::simple("Expected an iterable"))?;
                let result = PyList::empty(py);
                let mut errors: Option<HashMap<usize, DumpError>> = None;

                for (idx, item_result) in iter.enumerate() {
                    let v = item_result.map_err(|e| DumpError::simple(&e.to_string()))?;
                    match item.dump_to_py(&v) {
                        Ok(dumped) => {
                            result
                                .append(dumped)
                                .map_err(|e| DumpError::simple(&e.to_string()))?;
                        }
                        Err(e) => {
                            errors.get_or_insert_with(HashMap::new).insert(idx, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(DumpError::IndexMultiple(errors));
                }

                Ok(result.into_any().unbind())
            }
            Self::Union { variants } => {
                for variant in variants {
                    if let Ok(result) = variant.dump_to_py(value) {
                        return Ok(result);
                    }
                }
                Err(DumpError::simple("Value does not match any union variant"))
            }
        }
    }
}
