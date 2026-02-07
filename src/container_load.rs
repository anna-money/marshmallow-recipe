use std::collections::HashMap;

use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList, PySet, PyString, PyTuple};
use smallbitvec::SmallBitVec;

use crate::container::{DataclassContainer, FieldCommon, FieldContainer, TypeContainer};
use crate::error::LoadError;
use crate::fields::{
    any, bool_type, collection, date, datetime, decimal, dict, float_type, int_enum, int_type,
    str_enum, str_type, time, union, uuid,
};
use crate::slots::set_slot_value_direct;
use crate::utils::{call_validator, extract_error_args, get_object_cls, new_presized_dict, new_presized_list};

const NESTED_ERROR: &str = "Invalid input type.";

fn pyerrors_to_load_error(py: Python<'_>, errors: &Py<PyAny>) -> LoadError {
    let error = pyany_to_load_error(errors.bind(py));
    maybe_wrap_nested_error(error)
}

fn pyany_to_load_error(value: &Bound<'_, PyAny>) -> LoadError {
    if let Ok(s) = value.extract::<String>() {
        return LoadError::simple(&s);
    }
    if let Ok(list) = value.cast::<PyList>() {
        if list.is_empty() {
            return LoadError::messages(vec![]);
        }
        let all_strings = list.iter().all(|item| item.extract::<String>().is_ok());
        if all_strings {
            let msgs: Vec<String> = list
                .iter()
                .filter_map(|v| v.extract::<String>().ok())
                .collect();
            return LoadError::messages(msgs);
        }
        if list.len() == 1
            && let Ok(item) = list.get_item(0)
        {
            return pyany_to_load_error(&item);
        }
        let mut index_map = HashMap::with_capacity(list.len());
        for (idx, item) in list.iter().enumerate() {
            index_map.insert(idx, pyany_to_load_error(&item));
        }
        return LoadError::IndexMultiple(index_map);
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let mut map = HashMap::with_capacity(dict.len());
        for (k, v) in dict.iter() {
            let key = k.extract::<String>().unwrap_or_else(|_| k.to_string());
            map.insert(key, pyany_to_load_error(&v));
        }
        return LoadError::Multiple(map);
    }
    LoadError::simple(&value.to_string())
}

fn call_validator_with_error(
    validator: &Py<PyAny>,
    value: &Bound<'_, PyAny>,
) -> Result<(), LoadError> {
    let py = value.py();
    match call_validator(py, validator, value) {
        Ok(None) => Ok(()),
        Ok(Some(errors)) => Err(pyerrors_to_load_error(py, &errors)),
        Err(e) => {
            let error_value = extract_error_args(py, &e);
            let error = pyany_to_load_error(error_value.bind(py));
            Err(maybe_wrap_nested_error(error))
        }
    }
}

fn maybe_wrap_nested_error(e: LoadError) -> LoadError {
    match &e {
        LoadError::Multiple(_) | LoadError::Nested { .. } | LoadError::IndexMultiple(_) => {
            LoadError::ArrayWrapped(Box::new(e))
        }
        _ => e,
    }
}

#[allow(clippy::cast_sign_loss)]
impl FieldContainer {
    pub fn load_from_py(
        &self,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, LoadError> {
        let py = value.py();
        let common = self.common();

        if value.is_none() {
            if common.optional {
                return Ok(py.None());
            }
            let msg = common
                .none_error
                .as_deref()
                .unwrap_or("Field may not be null.");
            return Err(LoadError::simple(msg));
        }

        match self {
            Self::Str {
                strip_whitespaces, post_load, ..
            } => {
                let result = str_type::load_from_py(value, *strip_whitespaces, common.optional, common.invalid_error.as_deref())?;
                if let Some(post_load_fn) = post_load {
                    post_load_fn
                        .call1(py, (&result,))
                        .map_err(|e| LoadError::simple(&e.to_string()))
                } else {
                    Ok(result)
                }
            }
            Self::Int { .. } => int_type::load_from_py(value, common.invalid_error.as_deref()),
            Self::Float { .. } => {
                float_type::load_from_py(value, common.invalid_error.as_deref())
            }
            Self::Bool { .. } => bool_type::load_from_py(value, common.invalid_error.as_deref()),
            Self::Decimal { decimal_places, rounding, .. } => {
                decimal::load_from_py(value, *decimal_places, rounding.as_ref(), common.invalid_error.as_deref())
            }
            Self::Date { .. } => date::load_from_py(value, common.invalid_error.as_deref()),
            Self::Time { .. } => time::load_from_py(value, common.invalid_error.as_deref()),
            Self::DateTime { format, .. } => {
                datetime::load_from_py(value, format, common.invalid_error.as_deref())
            }
            Self::Uuid { .. } => uuid::load_from_py(value, common.invalid_error.as_deref()),
            Self::StrEnum { loader_data, .. } => str_enum::load_from_py(value, loader_data),
            Self::IntEnum { loader_data, .. } => int_enum::load_from_py(value, loader_data),
            Self::Any { .. } => Ok(any::load_from_py(value)),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => collection::load_from_py(
                value,
                *kind,
                item,
                item_validator.as_ref(),
                common.invalid_error.as_deref(),
            ),
            Self::Dict {
                value: value_schema,
                value_validator,
                ..
            } => dict::load_from_py(
                value,
                value_schema,
                value_validator.as_ref(),
                common.invalid_error.as_deref(),
            ),
            Self::Nested { container, .. } => container.load_from_py(value),
            Self::Union { variants, .. } => union::load_from_py(value, variants),
        }
    }
}

impl DataclassContainer {
    pub fn load_from_py(
        &self,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, LoadError> {
        let dict = value.cast::<PyDict>().map_err(|_| LoadError::Nested {
            field: "_schema".to_string(),
            inner: Box::new(LoadError::simple(NESTED_ERROR)),
        })?;

        if self.can_use_direct_slots {
            self.load_from_py_direct_slots(dict)
        } else {
            self.load_from_py_kwargs(dict)
        }
    }

    fn load_from_py_kwargs(
        &self,
        dict: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, LoadError> {
        let py = dict.py();
        let kwargs = new_presized_dict(py, self.fields.len());
        let mut seen = SmallBitVec::from_elem(self.fields.len(), false);
        let mut errors: Option<HashMap<String, LoadError>> = None;

        for (k, v) in dict.iter() {
            let key_str = k
                .cast::<PyString>()
                .ok()
                .and_then(|s| s.to_str().ok())
                .unwrap_or("");

            if let Some(&idx) = self.field_lookup.get(key_str) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();
                seen.set(idx, true);

                if !dc_field.field_init {
                    continue;
                }

                match dc_field.field.load_from_py(&v) {
                    Ok(py_val) => {
                        match apply_validate(
                            py,
                            py_val,
                            common.validator.as_ref(),
                        ) {
                            Ok(validated) => {
                                let _ = kwargs.set_item(dc_field.name_interned.bind(py), validated);
                            }
                            Err(e) => {
                                errors
                                    .get_or_insert_with(HashMap::new)
                                    .insert(dc_field.name.clone(), e);
                            }
                        }
                    }
                    Err(e) => {
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(dc_field.name.clone(), e);
                    }
                }
            }
        }

        for (idx, dc_field) in self.fields.iter().enumerate() {
            let common = dc_field.field.common();
            if errors
                .as_ref()
                .is_some_and(|e| e.contains_key(&dc_field.name))
            {
                continue;
            }
            if !seen[idx] && dc_field.field_init {
                match get_default_value(py, common) {
                    Ok(Some(val)) => {
                        let _ = kwargs.set_item(dc_field.name_interned.bind(py), val);
                    }
                    Ok(None) => {
                        let msg = common
                            .required_error
                            .as_deref()
                            .unwrap_or("Missing data for required field.");
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(dc_field.name.clone(), LoadError::simple(msg));
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
            return Err(LoadError::Multiple(errors));
        }

        self.cls
            .bind(py)
            .call((), Some(&kwargs))
            .map(Bound::unbind)
            .map_err(|e| LoadError::simple(&e.to_string()))
    }

    fn load_from_py_direct_slots(
        &self,
        dict: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, LoadError> {
        let py = dict.py();
        let object_type = get_object_cls(py).map_err(|e| LoadError::simple(&e.to_string()))?;
        let instance = object_type
            .call_method1(intern!(py, "__new__"), (self.cls.bind(py),))
            .map_err(|e| LoadError::simple(&e.to_string()))?;

        let mut field_values: Vec<Option<Py<PyAny>>> =
            (0..self.fields.len()).map(|_| None).collect();
        let mut errors: Option<HashMap<String, LoadError>> = None;

        for (k, v) in dict.iter() {
            let key_str = k
                .cast::<PyString>()
                .ok()
                .and_then(|s| s.to_str().ok())
                .unwrap_or("");

            if let Some(&idx) = self.field_lookup.get(key_str) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();

                match dc_field.field.load_from_py(&v) {
                    Ok(py_val) => {
                        match apply_validate(
                            py,
                            py_val,
                            common.validator.as_ref(),
                        ) {
                            Ok(validated) => {
                                field_values[idx] = Some(validated);
                            }
                            Err(e) => {
                                errors
                                    .get_or_insert_with(HashMap::new)
                                    .insert(dc_field.name.clone(), e);
                            }
                        }
                    }
                    Err(e) => {
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(dc_field.name.clone(), e);
                    }
                }
            }
        }

        for (idx, dc_field) in self.fields.iter().enumerate() {
            let common = dc_field.field.common();
            if errors
                .as_ref()
                .is_some_and(|e| e.contains_key(&dc_field.name))
            {
                continue;
            }
            let py_value = if let Some(value) = field_values[idx].take() {
                value
            } else {
                match get_default_value(py, common) {
                    Ok(Some(val)) => val,
                    Ok(None) => {
                        let msg = common
                            .required_error
                            .as_deref()
                            .unwrap_or("Missing data for required field.");
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(dc_field.name.clone(), LoadError::simple(msg));
                        continue;
                    }
                    Err(e) => {
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(dc_field.name.clone(), e);
                        continue;
                    }
                }
            };

            if let Some(offset) = dc_field.slot_offset {
                if !unsafe { set_slot_value_direct(&instance, offset, py_value) } {
                    errors
                        .get_or_insert_with(HashMap::new)
                        .insert(dc_field.name.clone(), LoadError::simple("Failed to set slot value: null object pointer"));
                }
            } else {
                instance
                    .setattr(dc_field.name_interned.bind(py), py_value)
                    .map_err(|e| LoadError::simple(&e.to_string()))?;
            }
        }

        if let Some(errors) = errors {
            return Err(LoadError::Multiple(errors));
        }

        Ok(instance.unbind())
    }
}

fn get_default_value(
    py: Python<'_>,
    common: &FieldCommon,
) -> Result<Option<Py<PyAny>>, LoadError> {
    if let Some(ref factory) = common.default_factory {
        return factory
            .call0(py)
            .map(Some)
            .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(ref value) = common.default_value {
        return Ok(Some(value.clone_ref(py)));
    }
    Ok(common.optional.then(|| py.None()))
}

fn apply_validate(
    py: Python<'_>,
    value: Py<PyAny>,
    validator: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, LoadError> {
    if let Some(validator) = validator {
        call_validator_with_error(validator, value.bind(py))?;
    }

    Ok(value)
}

impl TypeContainer {
    #[allow(clippy::too_many_lines)]
    pub fn load_from_py(
        &self,
        py: Python<'_>,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, LoadError> {
        match self {
            Self::Dataclass(dc) => dc.load_from_py(value),
            Self::Primitive(p) => {
                if value.is_none() {
                    return Ok(py.None());
                }
                p.field.load_from_py(value)
            }
            Self::List { item } => {
                let list = value
                    .cast::<PyList>()
                    .map_err(|_| LoadError::simple("Expected a list"))?;
                let result = new_presized_list(py, list.len());
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, v) in list.iter().enumerate() {
                    match item.load_from_py(py, &v) {
                        Ok(py_val) => unsafe {
                            pyo3::ffi::PyList_SET_ITEM(result.as_ptr(), idx.cast_signed(), py_val.into_ptr());
                        },
                        Err(e) => {
                            errors.get_or_insert_with(HashMap::new).insert(idx, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(LoadError::IndexMultiple(errors));
                }

                Ok(result.into_any().unbind())
            }
            Self::Dict { value: value_container } => {
                let dict = value
                    .cast::<PyDict>()
                    .map_err(|_| LoadError::simple("Expected a dict"))?;
                let result = new_presized_dict(py, dict.len());
                let mut errors: Option<HashMap<String, LoadError>> = None;

                for (k, v) in dict.iter() {
                    let key_str = k
                        .cast::<PyString>()
                        .ok()
                        .and_then(|s| s.to_str().ok())
                        .unwrap_or("");
                    match value_container.load_from_py(py, &v) {
                        Ok(py_val) => {
                            let _ = result.set_item(k, py_val);
                        }
                        Err(e) => {
                            errors
                                .get_or_insert_with(HashMap::new)
                                .insert(key_str.to_string(), e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(LoadError::Multiple(errors));
                }

                Ok(result.into_any().unbind())
            }
            Self::Optional { inner } => {
                if value.is_none() {
                    Ok(py.None())
                } else {
                    inner.load_from_py(py, value)
                }
            }
            Self::Set { item } => {
                if value.is_instance_of::<PyString>() {
                    return Err(LoadError::simple("Not a valid set."));
                }
                let iter = value
                    .try_iter()
                    .map_err(|_| LoadError::simple("Expected a set"))?;
                let (size_hint, _) = iter.size_hint();
                let mut items = Vec::with_capacity(size_hint);
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, item_result) in iter.enumerate() {
                    let v = item_result.map_err(|e| LoadError::simple(&e.to_string()))?;
                    match item.load_from_py(py, &v) {
                        Ok(py_val) => items.push(py_val),
                        Err(e) => {
                            errors.get_or_insert_with(HashMap::new).insert(idx, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(LoadError::IndexMultiple(errors));
                }

                PySet::new(py, &items)
                    .map(|s| s.into_any().unbind())
                    .map_err(|e| LoadError::simple(&e.to_string()))
            }
            Self::FrozenSet { item } => {
                if value.is_instance_of::<PyString>() {
                    return Err(LoadError::simple("Not a valid frozenset."));
                }
                let iter = value
                    .try_iter()
                    .map_err(|_| LoadError::simple("Expected a frozenset"))?;
                let (size_hint, _) = iter.size_hint();
                let mut items = Vec::with_capacity(size_hint);
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, item_result) in iter.enumerate() {
                    let v = item_result.map_err(|e| LoadError::simple(&e.to_string()))?;
                    match item.load_from_py(py, &v) {
                        Ok(py_val) => items.push(py_val),
                        Err(e) => {
                            errors.get_or_insert_with(HashMap::new).insert(idx, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(LoadError::IndexMultiple(errors));
                }

                PyFrozenSet::new(py, &items)
                    .map(|s| s.into_any().unbind())
                    .map_err(|e| LoadError::simple(&e.to_string()))
            }
            Self::Tuple { item } => {
                if value.is_instance_of::<PyString>() {
                    return Err(LoadError::simple("Not a valid tuple."));
                }
                let iter = value
                    .try_iter()
                    .map_err(|_| LoadError::simple("Expected a tuple"))?;
                let (size_hint, _) = iter.size_hint();
                let mut items = Vec::with_capacity(size_hint);
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, item_result) in iter.enumerate() {
                    let v = item_result.map_err(|e| LoadError::simple(&e.to_string()))?;
                    match item.load_from_py(py, &v) {
                        Ok(py_val) => items.push(py_val),
                        Err(e) => {
                            errors.get_or_insert_with(HashMap::new).insert(idx, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(LoadError::IndexMultiple(errors));
                }

                PyTuple::new(py, &items)
                    .map(|t| t.into_any().unbind())
                    .map_err(|e| LoadError::simple(&e.to_string()))
            }
            Self::Union { variants } => {
                let mut errors = Vec::new();
                for variant in variants {
                    match variant.load_from_py(py, value) {
                        Ok(result) => return Ok(result),
                        Err(e) => errors.push(e),
                    }
                }
                Err(LoadError::Array(errors))
            }
        }
    }
}
