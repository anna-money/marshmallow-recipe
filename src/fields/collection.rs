use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyFrozenSet, PyList, PySet, PyTuple};

use crate::container::FieldContainer;
use crate::error::{DumpError, LoadError};
use crate::error_convert::pyerrors_to_dump_error;
use crate::utils::{call_validator, new_presized_list};

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

fn pyerrors_to_load_error(py: Python<'_>, errors: &Py<PyAny>) -> LoadError {
    use pyo3::types::{PyDict, PyList as PyListType};

    fn pyany_to_load_error(value: &Bound<'_, PyAny>) -> LoadError {
        if let Ok(s) = value.extract::<String>() {
            return LoadError::simple(&s);
        }
        if let Ok(list) = value.cast::<PyListType>() {
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

    fn maybe_wrap_nested_error(e: LoadError) -> LoadError {
        match &e {
            LoadError::Multiple(_) | LoadError::Nested { .. } | LoadError::IndexMultiple(_) => {
                LoadError::ArrayWrapped(Box::new(e))
            }
            _ => e,
        }
    }

    let error = pyany_to_load_error(errors.bind(py));
    maybe_wrap_nested_error(error)
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
                if let Some(validator) = item_validator
                    && let Ok(Some(err_list)) =
                        call_validator(py, validator, py_val.bind(py))
                {
                    errors
                        .get_or_insert_with(HashMap::new)
                        .insert(idx, pyerrors_to_load_error(py, &err_list));
                    continue;
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

    let size = value.len().map_err(|e| DumpError::simple(&e.to_string()))?;
    let result = new_presized_list(py, size);
    let mut errors: Option<HashMap<usize, DumpError>> = None;

    let iter = value.try_iter().map_err(|_| DumpError::simple(err_msg))?;
    let mut idx = 0usize;

    for item_result in iter {
        let item_value = item_result.map_err(|e| DumpError::simple(&e.to_string()))?;

        if let Some(validator) = item_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &item_value)
        {
            errors
                .get_or_insert_with(HashMap::new)
                .insert(idx, pyerrors_to_dump_error(py, &err_list));
            idx += 1;
            continue;
        }

        match item.dump_to_py(&item_value) {
            Ok(dumped) => unsafe {
                pyo3::ffi::PyList_SET_ITEM(result.as_ptr(), idx.cast_signed(), dumped.into_ptr());
            },
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
