use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::dumper::dump_dataclass;
use crate::types::DumpContext;
use crate::types::{TypeDescriptor, TypeKind};

fn dump_root_type<'py>(
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    ctx: &DumpContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    match descriptor.type_kind {
        TypeKind::Dataclass => {
            let dumper_fields = descriptor.dumper_fields.as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing dumper_fields for dataclass"))?;
            dump_dataclass(value, dumper_fields, ctx)
        }
        TypeKind::Primitive => {
            if value.is_none() {
                return Ok(ctx.py.None());
            }
            let dumper = descriptor.primitive_dumper.as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_dumper"))?;
            dumper.dump_to_dict(value, "", ctx)
        }
        TypeKind::List => {
            let list = value.cast::<PyList>()?;
            let item_descriptor = descriptor.item_type.as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for list"))?;

            let result = PyList::empty(ctx.py);
            for item in list.iter() {
                result.append(dump_root_type(&item, item_descriptor, ctx)?)?;
            }
            Ok(result.into_any().unbind())
        }
        TypeKind::Dict => {
            let dict = value.cast::<PyDict>()?;
            let value_descriptor = descriptor.value_type.as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict"))?;

            let result = PyDict::new(ctx.py);
            for (k, v) in dict.iter() {
                result.set_item(k, dump_root_type(&v, value_descriptor, ctx)?)?;
            }
            Ok(result.into_any().unbind())
        }
        TypeKind::Optional => {
            if value.is_none() {
                Ok(ctx.py.None())
            } else {
                let inner_descriptor = descriptor.inner_type.as_ref()
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type for optional"))?;
                dump_root_type(value, inner_descriptor, ctx)
            }
        }
        TypeKind::Set | TypeKind::FrozenSet | TypeKind::Tuple => {
            let item_descriptor = descriptor.item_type.as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for collection"))?;

            let result = PyList::empty(ctx.py);
            for item_result in value.try_iter()? {
                result.append(dump_root_type(&item_result?, item_descriptor, ctx)?)?;
            }
            Ok(result.into_any().unbind())
        }
        TypeKind::Union => {
            let variants = descriptor.union_variants.as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union"))?;

            for variant in variants {
                if let Ok(result) = dump_root_type(value, variant, ctx) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value does not match any union variant",
            ))
        }
    }
}

pub fn dump<'py>(
    py: Python<'py>,
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    none_value_handling: Option<&str>,
    global_decimal_places: Option<i32>,
) -> PyResult<Py<PyAny>> {
    let ctx = DumpContext {
        py,
        none_value_handling,
        global_decimal_places,
    };

    dump_root_type(value, descriptor, &ctx)
}
