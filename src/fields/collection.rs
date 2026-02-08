use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList, PySet, PyString, PyTuple};

use crate::container::FieldContainer;
use crate::error::{DumpError, LoadError};
use crate::error_convert::pyerrors_to_dump_error;
use crate::utils::{call_validator, new_presized_list};

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
    fn pyany_to_load_error(py: Python<'_>, value: &Bound<'_, PyAny>) -> LoadError {
        if let Ok(s) = value.extract::<String>() {
            return LoadError::simple(py, &s);
        }
        if let Ok(list) = value.cast::<PyList>() {
            if list.is_empty() {
                return LoadError::List(list.clone().unbind());
            }
            let all_strings = list.iter().all(|item| item.extract::<String>().is_ok());
            if all_strings {
                return LoadError::List(list.clone().unbind());
            }
            if list.len() == 1
                && let Ok(item) = list.get_item(0)
            {
                return pyany_to_load_error(py, &item);
            }
            let dict = PyDict::new(py);
            for (idx, item) in list.iter().enumerate() {
                let _ = dict.set_item(idx, pyany_to_load_error(py, &item).to_py_value(py).unwrap_or_else(|_| py.None()));
            }
            return LoadError::Dict(dict.unbind());
        }
        if let Ok(dict) = value.cast::<PyDict>() {
            let result = PyDict::new(py);
            for (k, v) in dict.iter() {
                let _ = result.set_item(&k, pyany_to_load_error(py, &v).to_py_value(py).unwrap_or_else(|_| py.None()));
            }
            return LoadError::Dict(result.unbind());
        }
        LoadError::simple(py, &value.to_string())
    }

    fn maybe_wrap_nested_error(py: Python<'_>, e: LoadError) -> LoadError {
        match e {
            LoadError::Dict(d) => {
                let val = d.into_any();
                LoadError::List(PyList::new(py, [val.bind(py)]).expect("single element").unbind())
            }
            other => other,
        }
    }

    let error = pyany_to_load_error(py, errors.bind(py));
    maybe_wrap_nested_error(py, error)
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, LoadError> {
    let py = value.py();

    let is_valid_sequence = value.is_instance_of::<PyList>()
        || value.is_instance_of::<PyTuple>()
        || value.is_instance_of::<PySet>()
        || value.is_instance_of::<PyFrozenSet>();
    if !is_valid_sequence {
        return Err(LoadError::Single(invalid_error.clone_ref(py)));
    }

    let iter = value.try_iter().map_err(|_| LoadError::Single(invalid_error.clone_ref(py)))?;
    let (size_hint, _) = iter.size_hint();
    let mut items = Vec::with_capacity(size_hint);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (idx, item_result) in iter.enumerate() {
        let v = item_result.map_err(|e| LoadError::simple(py, &e.to_string()))?;
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
                    let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                    let _ = err_dict.set_item(
                        idx,
                        pyerrors_to_load_error(py, &err_list).to_py_value(py).unwrap_or_else(|_| py.None()),
                    );
                    continue;
                }
                items.push(py_val);
            }
            Err(e) => {
                let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                let _ = err_dict.set_item(idx, e.to_py_value(py).unwrap_or_else(|_| py.None()));
            }
        }
    }

    if let Some(errors) = errors {
        return Err(LoadError::Dict(errors.unbind()));
    }

    match kind {
        CollectionKind::List => PyList::new(py, items)
            .map(|l| l.into_any().unbind())
            .map_err(|e| LoadError::simple(py, &e.to_string())),
        CollectionKind::Set => PySet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| LoadError::simple(py, &e.to_string())),
        CollectionKind::FrozenSet => PyFrozenSet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| LoadError::simple(py, &e.to_string())),
        CollectionKind::Tuple => PyTuple::new(py, &items)
            .map(|t| t.into_any().unbind())
            .map_err(|e| LoadError::simple(py, &e.to_string())),
    }
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, DumpError> {
    let py = value.py();

    if !kind.is_valid_type(value) {
        return Err(DumpError::Single(invalid_error.clone_ref(py)));
    }

    let size = value.len().map_err(|e| DumpError::simple(py, &e.to_string()))?;
    let result = new_presized_list(py, size);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    let iter = value.try_iter().map_err(|_| DumpError::Single(invalid_error.clone_ref(py)))?;
    let mut idx = 0usize;

    for item_result in iter {
        let item_value = item_result.map_err(|e| DumpError::simple(py, &e.to_string()))?;

        if let Some(validator) = item_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &item_value)
        {
            let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
            let _ = err_dict.set_item(
                idx,
                pyerrors_to_dump_error(py, &err_list).to_py_value(py).unwrap_or_else(|_| py.None()),
            );
            idx += 1;
            continue;
        }

        match item.dump_to_py(&item_value) {
            Ok(dumped) => unsafe {
                pyo3::ffi::PyList_SET_ITEM(result.as_ptr(), idx.cast_signed(), dumped.into_ptr());
            },
            Err(e) => {
                let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                let _ = err_dict.set_item(idx, e.to_py_value(py).unwrap_or_else(|_| py.None()));
            }
        }
        idx += 1;
    }

    if let Some(errors) = errors {
        return Err(DumpError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}
