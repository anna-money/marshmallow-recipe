use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList, PySet, PyString, PyTuple};

use crate::loader::load_dataclass_from_parts;
use crate::utils::{extract_error_args, wrap_err_dict_idx};
pub use crate::types::LoadContext;
use crate::types::{TypeDescriptor, TypeKind};

fn wrap_err_dict_for_field(py: Python, field_name: &str, inner: Py<PyAny>) -> Py<PyAny> {
    if field_name.is_empty() {
        return inner;
    }
    let dict = PyDict::new(py);
    dict.set_item(field_name, inner).unwrap();
    dict.into()
}

fn load_iterable_items<'py>(
    value: &Bound<'py, PyAny>,
    item_descriptor: &TypeDescriptor,
    ctx: &LoadContext<'py>,
) -> PyResult<Bound<'py, PyList>> {
    let len_hint = value.len().unwrap_or(0);
    let mut items: Vec<Py<PyAny>> = Vec::with_capacity(len_hint);
    for (idx, item) in value.try_iter()?.enumerate() {
        let item = item?;
        match load_root_type(&item, item_descriptor, ctx) {
            Ok(v) => items.push(v),
            Err(e) => {
                let inner = extract_error_args(ctx.py, &e);
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict_idx(ctx.py, idx, inner),
                ));
            }
        }
    }
    PyList::new(ctx.py, items)
}

#[allow(clippy::too_many_lines)]
pub fn load_root_type<'py>(
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    ctx: &LoadContext<'py>,
) -> PyResult<Py<PyAny>> {
    match descriptor.type_kind {
        TypeKind::Dataclass => {
            let cls = descriptor.cls.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing cls for dataclass")
            })?;
            let cls_bound = cls.bind(ctx.py);
            let loader_fields = descriptor.loader_fields.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing loader_fields for dataclass")
            })?;
            load_dataclass_from_parts(
                value, cls_bound, loader_fields, &descriptor.field_lookup,
                descriptor.can_use_direct_slots, ctx
            )
        }
        TypeKind::Primitive => {
            if value.is_none() {
                return Ok(ctx.py.None());
            }
            let loader = descriptor.primitive_loader.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_loader")
            })?;
            loader.load_from_dict(value, "", None, ctx)
        }
        TypeKind::List => {
            let list = value.cast::<PyList>().map_err(|_| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a list")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for list")
            })?;

            let mut items: Vec<Py<PyAny>> = Vec::with_capacity(list.len());
            for (idx, item) in list.iter().enumerate() {
                match load_root_type(&item, item_descriptor, ctx) {
                    Ok(v) => items.push(v),
                    Err(e) => {
                        let inner = extract_error_args(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict_idx(ctx.py, idx, inner),
                        ));
                    }
                }
            }
            Ok(PyList::new(ctx.py, items)?.into_any().unbind())
        }
        TypeKind::Dict => {
            let dict = value.cast::<PyDict>().map_err(|_| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a dict")
            })?;
            let value_descriptor = descriptor.value_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict")
            })?;

            let result = PyDict::new(ctx.py);
            for (k, v) in dict.iter() {
                match load_root_type(&v, value_descriptor, ctx) {
                    Ok(val) => result.set_item(k, val)?,
                    Err(e) => {
                        let key_str = k
                            .cast::<PyString>()
                            .ok()
                            .and_then(|s| s.to_str().ok())
                            .unwrap_or("");
                        let inner = extract_error_args(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict_for_field(ctx.py, key_str, inner),
                        ));
                    }
                }
            }
            Ok(result.into_any().unbind())
        }
        TypeKind::Optional => {
            if value.is_none() {
                Ok(ctx.py.None())
            } else {
                let inner_descriptor = descriptor.inner_type.as_ref().ok_or_else(|| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type for optional")
                })?;
                load_root_type(value, inner_descriptor, ctx)
            }
        }
        TypeKind::Set | TypeKind::FrozenSet | TypeKind::Tuple => {
            let (type_name, missing_msg) = match descriptor.type_kind {
                TypeKind::Set => ("set", "Missing item_type for set"),
                TypeKind::FrozenSet => ("frozenset", "Missing item_type for frozenset"),
                TypeKind::Tuple => ("tuple", "Missing item_type for tuple"),
                _ => unreachable!(),
            };

            if value.is_instance_of::<PyString>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Not a valid {type_name}."),
                ));
            }

            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(missing_msg)
            })?;

            let items = load_iterable_items(value, item_descriptor, ctx)?;

            match descriptor.type_kind {
                TypeKind::Set => Ok(PySet::new(ctx.py, items.iter())?.into_any().unbind()),
                TypeKind::FrozenSet => Ok(PyFrozenSet::new(ctx.py, items.iter())?.into_any().unbind()),
                TypeKind::Tuple => Ok(PyTuple::new(ctx.py, items.iter())?.into_any().unbind()),
                _ => unreachable!(),
            }
        }
        TypeKind::Union => {
            let variants = descriptor.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union")
            })?;

            for variant in variants {
                if let Ok(result) = load_root_type(value, variant, ctx) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value does not match any union variant",
            ))
        }
    }
}

pub fn load<'py>(
    py: Python<'py>,
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    decimal_places: Option<i32>,
) -> PyResult<Py<PyAny>> {
    let ctx = LoadContext::new(py, decimal_places);

    load_root_type(value, descriptor, &ctx)
}
