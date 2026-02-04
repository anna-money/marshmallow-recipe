use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyFrozenSet, PyList, PySet, PyTuple};

use crate::container::FieldContainer;
use crate::error::{DumpError, LoadError};
use crate::error_convert::{pyerrors_to_dump_error, pyerrors_to_load_error};
use crate::utils::call_validator;

const LIST_ERROR: &str = "Not a valid list.";
const SET_ERROR: &str = "Not a valid set.";
const FROZENSET_ERROR: &str = "Not a valid frozenset.";
const TUPLE_ERROR: &str = "Not a valid tuple.";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CollectionKind {
    List,
    Set,
    FrozenSet,
    Tuple,
}

impl CollectionKind {
    pub fn is_valid_type(self, value: &Bound<'_, PyAny>) -> bool {
        match self {
            Self::List => value.is_instance_of::<PyList>(),
            Self::Set => value.is_instance_of::<PySet>(),
            Self::FrozenSet => value.is_instance_of::<PyFrozenSet>(),
            Self::Tuple => value.is_instance_of::<PyTuple>(),
        }
    }
}

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let default_err = match kind {
        CollectionKind::List => LIST_ERROR,
        CollectionKind::Set => SET_ERROR,
        CollectionKind::FrozenSet => FROZENSET_ERROR,
        CollectionKind::Tuple => TUPLE_ERROR,
    };
    let err_msg = invalid_error.unwrap_or(default_err);

    let arr = value
        .as_array()
        .ok_or_else(|| LoadError::simple(err_msg))?;

    let mut items = Vec::with_capacity(arr.len());
    let mut errors: Option<HashMap<usize, LoadError>> = None;

    for (idx, v) in arr.iter().enumerate() {
        if v.is_null() {
            items.push(py.None());
            continue;
        }
        match item.load(py, v) {
            Ok(py_val) => {
                if let Some(validator) = item_validator {
                    if let Ok(Some(err_list)) =
                        call_validator(py, validator, py_val.bind(py))
                    {
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(idx, pyerrors_to_load_error(py, &err_list));
                        continue;
                    }
                }
                items.push(py_val);
            }
            Err(e) => {
                errors.get_or_insert_with(HashMap::new).insert(idx, e);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(LoadError::IndexMultiple(errors));
    }

    match kind {
        CollectionKind::List => PyList::new(py, items)
            .map(|l| l.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
        CollectionKind::Set => PySet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
        CollectionKind::FrozenSet => PyFrozenSet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
        CollectionKind::Tuple => PyTuple::new(py, &items)
            .map(|t| t.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
    }
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let default_err = match kind {
        CollectionKind::List => LIST_ERROR,
        CollectionKind::Set => SET_ERROR,
        CollectionKind::FrozenSet => FROZENSET_ERROR,
        CollectionKind::Tuple => TUPLE_ERROR,
    };
    let err_msg = invalid_error.unwrap_or(default_err);
    let py = value.py();

    let is_valid_sequence = value.is_instance_of::<PyList>()
        || value.is_instance_of::<PyTuple>()
        || value.is_instance_of::<PySet>()
        || value.is_instance_of::<PyFrozenSet>();
    if !is_valid_sequence {
        return Err(LoadError::simple(err_msg));
    }

    let iter = value.try_iter().map_err(|_| LoadError::simple(err_msg))?;
    let (size_hint, _) = iter.size_hint();
    let mut items = Vec::with_capacity(size_hint);
    let mut errors: Option<HashMap<usize, LoadError>> = None;

    for (idx, item_result) in iter.enumerate() {
        let v = item_result.map_err(|e| LoadError::simple(&e.to_string()))?;
        if v.is_none() {
            items.push(py.None());
            continue;
        }
        match item.load_from_py(&v) {
            Ok(py_val) => {
                if let Some(validator) = item_validator {
                    if let Ok(Some(err_list)) =
                        call_validator(py, validator, py_val.bind(py))
                    {
                        errors
                            .get_or_insert_with(HashMap::new)
                            .insert(idx, pyerrors_to_load_error(py, &err_list));
                        continue;
                    }
                }
                items.push(py_val);
            }
            Err(e) => {
                errors.get_or_insert_with(HashMap::new).insert(idx, e);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(LoadError::IndexMultiple(errors));
    }

    match kind {
        CollectionKind::List => PyList::new(py, items)
            .map(|l| l.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
        CollectionKind::Set => PySet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
        CollectionKind::FrozenSet => PyFrozenSet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
        CollectionKind::Tuple => PyTuple::new(py, &items)
            .map(|t| t.into_any().unbind())
            .map_err(|e| LoadError::simple(&e.to_string())),
    }
}

pub fn dump(
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
) -> Result<serde_json::Value, DumpError> {
    let err_msg = match kind {
        CollectionKind::List => LIST_ERROR,
        CollectionKind::Set | CollectionKind::FrozenSet => SET_ERROR,
        CollectionKind::Tuple => TUPLE_ERROR,
    };
    let py = value.py();

    if !kind.is_valid_type(value) {
        return Err(DumpError::simple(err_msg));
    }

    let iter = value
        .try_iter()
        .map_err(|_| DumpError::simple(err_msg))?;

    let (size_hint, _) = iter.size_hint();
    let mut items = Vec::with_capacity(size_hint);
    let mut errors: Option<HashMap<usize, DumpError>> = None;
    let mut idx = 0usize;

    for item_result in iter {
        let item_value = item_result.map_err(|e| DumpError::simple(&e.to_string()))?;

        if let Some(validator) = item_validator {
            if let Ok(Some(err_list)) = call_validator(py, validator, &item_value) {
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(idx, pyerrors_to_dump_error(py, &err_list));
                idx += 1;
                continue;
            }
        }

        match item.dump(&item_value) {
            Ok(dumped) => items.push(dumped),
            Err(e) => {
                errors.get_or_insert_with(HashMap::new).insert(idx, e);
            }
        }
        idx += 1;
    }

    if let Some(errors) = errors {
        return Err(DumpError::IndexMultiple(errors));
    }

    Ok(serde_json::Value::Array(items))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, DumpError> {
    let err_msg = match kind {
        CollectionKind::List => LIST_ERROR,
        CollectionKind::Set | CollectionKind::FrozenSet => SET_ERROR,
        CollectionKind::Tuple => TUPLE_ERROR,
    };
    let py = value.py();

    if !kind.is_valid_type(value) {
        return Err(DumpError::simple(err_msg));
    }

    let iter = value.try_iter().map_err(|_| DumpError::simple(err_msg))?;

    let result = PyList::empty(py);
    let mut errors: Option<HashMap<usize, DumpError>> = None;
    let mut idx = 0usize;

    for item_result in iter {
        let item_value = item_result.map_err(|e| DumpError::simple(&e.to_string()))?;

        if let Some(validator) = item_validator {
            if let Ok(Some(err_list)) = call_validator(py, validator, &item_value) {
                errors
                    .get_or_insert_with(HashMap::new)
                    .insert(idx, pyerrors_to_dump_error(py, &err_list));
                idx += 1;
                continue;
            }
        }

        match item.dump_to_py(&item_value) {
            Ok(dumped) => {
                result
                    .append(dumped)
                    .map_err(|e| DumpError::simple(&e.to_string()))?;
            }
            Err(e) => {
                errors.get_or_insert_with(HashMap::new).insert(idx, e);
            }
        }
        idx += 1;
    }

    if let Some(errors) = errors {
        return Err(DumpError::IndexMultiple(errors));
    }

    Ok(result.into_any().unbind())
}
