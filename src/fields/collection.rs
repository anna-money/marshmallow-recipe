use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList, PySet, PyString, PyTuple};

use crate::container::FieldContainer;
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
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

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    let is_valid_sequence = value.is_instance_of::<PyList>()
        || value.is_instance_of::<PyTuple>()
        || value.is_instance_of::<PySet>()
        || value.is_instance_of::<PyFrozenSet>();
    if !is_valid_sequence {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let iter = value
        .try_iter()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
    let (size_hint, _) = iter.size_hint();
    let mut items = Vec::with_capacity(size_hint);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (idx, item_result) in iter.enumerate() {
        let v = item_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if v.is_none() {
            items.push(py.None());
            continue;
        }
        match item.load_from_py(&v) {
            Ok(py_val) => {
                if let Some(validator) = item_validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, py_val.bind(py))
                {
                    let e = pyerrors_to_serialization_error(py, &err_list);
                    accumulate_error(py, &mut errors, idx, &e);
                    continue;
                }
                items.push(py_val);
            }
            Err(ref e) => accumulate_error(py, &mut errors, idx, e),
        }
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    match kind {
        CollectionKind::List => PyList::new(py, items)
            .map(|l| l.into_any().unbind())
            .map_err(|e| SerializationError::simple(py, &e.to_string())),
        CollectionKind::Set => PySet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| SerializationError::simple(py, &e.to_string())),
        CollectionKind::FrozenSet => PyFrozenSet::new(py, &items)
            .map(|s| s.into_any().unbind())
            .map_err(|e| SerializationError::simple(py, &e.to_string())),
        CollectionKind::Tuple => PyTuple::new(py, &items)
            .map(|t| t.into_any().unbind())
            .map_err(|e| SerializationError::simple(py, &e.to_string())),
    }
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if !kind.is_valid_type(value) {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let size = value
        .len()
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    let result = new_presized_list(py, size);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    let iter = value
        .try_iter()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
    let mut idx = 0usize;

    for item_result in iter {
        let item_value = item_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        if let Some(validator) = item_validator
            && let Ok(Some(err_list)) = call_validator(py, validator, &item_value)
        {
            let e = pyerrors_to_serialization_error(py, &err_list);
            accumulate_error(py, &mut errors, idx, &e);
            idx += 1;
            continue;
        }

        match item.dump_to_py(&item_value) {
            Ok(dumped) => unsafe {
                pyo3::ffi::PyList_SET_ITEM(result.as_ptr(), idx.cast_signed(), dumped.into_ptr());
            },
            Err(ref e) => accumulate_error(py, &mut errors, idx, e),
        }
        idx += 1;
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}
