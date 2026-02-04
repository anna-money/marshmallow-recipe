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
use crate::utils::{call_validator, extract_error_args, get_object_cls, pyany_to_json_value};

const NESTED_ERROR: &str = "Invalid input type.";

fn pyerrors_to_load_error(py: Python<'_>, errors: &Py<PyAny>) -> LoadError {
    let json_value = pyany_to_json_value(errors.bind(py));
    let error = json_value_to_load_error(&json_value);
    maybe_wrap_nested_error(error)
}

fn json_value_to_load_error(value: &serde_json::Value) -> LoadError {
    match value {
        serde_json::Value::Array(arr) => {
            if arr.is_empty() {
                return LoadError::messages(vec![]);
            }
            if arr.iter().all(serde_json::Value::is_string) {
                let msgs: Vec<String> = arr
                    .iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect();
                LoadError::messages(msgs)
            } else if arr.len() == 1 {
                json_value_to_load_error(&arr[0])
            } else {
                let mut index_map = HashMap::with_capacity(arr.len());
                for (idx, v) in arr.iter().enumerate() {
                    index_map.insert(idx, json_value_to_load_error(v));
                }
                LoadError::IndexMultiple(index_map)
            }
        }
        serde_json::Value::Object(obj) => {
            let mut map = HashMap::with_capacity(obj.len());
            for (k, v) in obj {
                map.insert(k.clone(), json_value_to_load_error(v));
            }
            LoadError::Multiple(map)
        }
        serde_json::Value::String(s) => LoadError::simple(s),
        _ => LoadError::simple(&value.to_string()),
    }
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
            let json_value = pyany_to_json_value(error_value.bind(py));
            let error = json_value_to_load_error(&json_value);
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
    pub fn load(
        &self,
        py: Python<'_>,
        value: &serde_json::Value,
    ) -> Result<Py<PyAny>, LoadError> {
        let common = self.common();

        if value.is_null() {
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
                strip_whitespaces, ..
            } => str_type::load(py, value, *strip_whitespaces, common.invalid_error.as_deref()),
            Self::Int { .. } => int_type::load(py, value, common.invalid_error.as_deref()),
            Self::Float { .. } => float_type::load(py, value, common.invalid_error.as_deref()),
            Self::Bool { .. } => bool_type::load(py, value, common.invalid_error.as_deref()),
            Self::Decimal { decimal_places, rounding, .. } => {
                decimal::load(py, value, *decimal_places, rounding.as_ref(), common.invalid_error.as_deref())
            }
            Self::Date { .. } => date::load(py, value, common.invalid_error.as_deref()),
            Self::Time { .. } => time::load(py, value, common.invalid_error.as_deref()),
            Self::DateTime { format, .. } => {
                datetime::load(py, value, format, common.invalid_error.as_deref())
            }
            Self::Uuid { .. } => uuid::load(py, value, common.invalid_error.as_deref()),
            Self::StrEnum { loader_data, .. } => str_enum::load(py, value, loader_data),
            Self::IntEnum { loader_data, .. } => int_enum::load(py, value, loader_data),
            Self::Any { .. } => any::load(py, value),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => collection::load(
                py,
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
            } => dict::load(
                py,
                value,
                value_schema,
                value_validator.as_ref(),
                common.invalid_error.as_deref(),
            ),
            Self::Nested { container, .. } => container.load(py, value),
            Self::Union { variants, .. } => union::load(py, value, variants),
        }
    }

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
                strip_whitespaces, ..
            } => str_type::load_from_py(value, *strip_whitespaces, common.invalid_error.as_deref()),
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
    pub fn load(
        &self,
        py: Python<'_>,
        value: &serde_json::Value,
    ) -> Result<Py<PyAny>, LoadError> {
        let obj = value.as_object().ok_or_else(|| LoadError::Nested {
            field: "_schema".to_string(),
            inner: Box::new(LoadError::simple(NESTED_ERROR)),
        })?;

        if self.can_use_direct_slots {
            self.load_direct_slots(py, obj)
        } else {
            self.load_kwargs(py, obj)
        }
    }

    fn load_kwargs(
        &self,
        py: Python<'_>,
        obj: &serde_json::Map<String, serde_json::Value>,
    ) -> Result<Py<PyAny>, LoadError> {
        let kwargs = PyDict::new(py);
        let mut seen = SmallBitVec::from_elem(self.fields.len(), false);
        let mut errors: Option<HashMap<String, LoadError>> = None;

        for (key, value) in obj {
            if let Some(&idx) = self.field_lookup.get(key.as_str()) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();
                seen.set(idx, true);

                if !dc_field.field_init {
                    continue;
                }

                match dc_field.field.load(py, value) {
                    Ok(py_val) => {
                        match apply_post_load_and_validate(
                            py,
                            py_val,
                            dc_field.post_load.as_ref(),
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

    fn load_direct_slots(
        &self,
        py: Python<'_>,
        obj: &serde_json::Map<String, serde_json::Value>,
    ) -> Result<Py<PyAny>, LoadError> {
        let object_type = get_object_cls(py).map_err(|e| LoadError::simple(&e.to_string()))?;
        let instance = object_type
            .call_method1(intern!(py, "__new__"), (self.cls.bind(py),))
            .map_err(|e| LoadError::simple(&e.to_string()))?;

        let mut field_values: Vec<Option<Py<PyAny>>> =
            (0..self.fields.len()).map(|_| None).collect();
        let mut errors: Option<HashMap<String, LoadError>> = None;

        for (key, value) in obj {
            if let Some(&idx) = self.field_lookup.get(key.as_str()) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();

                match dc_field.field.load(py, value) {
                    Ok(py_val) => {
                        match apply_post_load_and_validate(
                            py,
                            py_val,
                            dc_field.post_load.as_ref(),
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
        let kwargs = PyDict::new(py);
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
                        match apply_post_load_and_validate(
                            py,
                            py_val,
                            dc_field.post_load.as_ref(),
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
                        match apply_post_load_and_validate(
                            py,
                            py_val,
                            dc_field.post_load.as_ref(),
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

fn apply_post_load_and_validate(
    py: Python<'_>,
    value: Py<PyAny>,
    post_load: Option<&Py<PyAny>>,
    validator: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, LoadError> {
    let mut result = value;

    if let Some(post_load_fn) = post_load {
        result = post_load_fn
            .call1(py, (result,))
            .map_err(|e| LoadError::simple(&e.to_string()))?;
    }

    if let Some(validator) = validator {
        call_validator_with_error(validator, result.bind(py))?;
    }

    Ok(result)
}

pub fn load_from_bytes_with_container(
    py: Python<'_>,
    json_bytes: &[u8],
    container: &TypeContainer,
) -> PyResult<Py<PyAny>> {
    let value: serde_json::Value = serde_json::from_slice(json_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    container.load(py, &value).map_err(|e| e.to_py_err(py))
}

impl TypeContainer {
    #[allow(clippy::too_many_lines)]
    pub fn load(
        &self,
        py: Python<'_>,
        value: &serde_json::Value,
    ) -> Result<Py<PyAny>, LoadError> {
        match self {
            Self::Dataclass(dc) => dc.load(py, value),
            Self::Primitive(p) => {
                if value.is_null() {
                    return Ok(py.None());
                }
                p.field.load(py, value)
            }
            Self::List { item } => {
                let arr = value
                    .as_array()
                    .ok_or_else(|| LoadError::simple("Expected a list"))?;
                let mut items = Vec::with_capacity(arr.len());
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, v) in arr.iter().enumerate() {
                    match item.load(py, v) {
                        Ok(py_val) => items.push(py_val),
                        Err(e) => {
                            errors.get_or_insert_with(HashMap::new).insert(idx, e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(LoadError::IndexMultiple(errors));
                }

                PyList::new(py, items)
                    .map(|l| l.into_any().unbind())
                    .map_err(|e| LoadError::simple(&e.to_string()))
            }
            Self::Dict { value: value_container } => {
                let obj = value
                    .as_object()
                    .ok_or_else(|| LoadError::simple("Expected a dict"))?;
                let dict = PyDict::new(py);
                let mut errors: Option<HashMap<String, LoadError>> = None;

                for (key, v) in obj {
                    match value_container.load(py, v) {
                        Ok(py_val) => {
                            let _ = dict.set_item(key.as_str(), py_val);
                        }
                        Err(e) => {
                            errors
                                .get_or_insert_with(HashMap::new)
                                .insert(key.clone(), e);
                        }
                    }
                }

                if let Some(errors) = errors {
                    return Err(LoadError::Multiple(errors));
                }

                Ok(dict.into_any().unbind())
            }
            Self::Optional { inner } => {
                if value.is_null() {
                    Ok(py.None())
                } else {
                    inner.load(py, value)
                }
            }
            Self::Set { item } => {
                let arr = value
                    .as_array()
                    .ok_or_else(|| LoadError::simple("Expected a set"))?;
                let mut items = Vec::with_capacity(arr.len());
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, v) in arr.iter().enumerate() {
                    match item.load(py, v) {
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
                let arr = value
                    .as_array()
                    .ok_or_else(|| LoadError::simple("Expected a frozenset"))?;
                let mut items = Vec::with_capacity(arr.len());
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, v) in arr.iter().enumerate() {
                    match item.load(py, v) {
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
                let arr = value
                    .as_array()
                    .ok_or_else(|| LoadError::simple("Expected a tuple"))?;
                let mut items = Vec::with_capacity(arr.len());
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, v) in arr.iter().enumerate() {
                    match item.load(py, v) {
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
                    match variant.load(py, value) {
                        Ok(result) => return Ok(result),
                        Err(e) => errors.push(e),
                    }
                }
                Err(LoadError::Array(errors))
            }
        }
    }

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
                let mut items = Vec::with_capacity(list.len());
                let mut errors: Option<HashMap<usize, LoadError>> = None;

                for (idx, v) in list.iter().enumerate() {
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

                PyList::new(py, items)
                    .map(|l| l.into_any().unbind())
                    .map_err(|e| LoadError::simple(&e.to_string()))
            }
            Self::Dict { value: value_container } => {
                let dict = value
                    .cast::<PyDict>()
                    .map_err(|_| LoadError::simple("Expected a dict"))?;
                let result = PyDict::new(py);
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
                let mut items = Vec::new();
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
                let mut items = Vec::new();
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
                let mut items = Vec::new();
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
