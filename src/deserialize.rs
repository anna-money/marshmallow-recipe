use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};
use uuid::Uuid;

use crate::cache::get_cached_types;
use crate::slots::set_slot_value_direct;
use crate::types::{FieldDescriptor, FieldType, TypeDescriptor, TypeKind};

fn err_dict(py: Python, field_name: &str, message: &str) -> Py<PyAny> {
    let errors = PyList::empty(py);
    errors.append(message).unwrap();
    if field_name.is_empty() {
        return errors.into();
    }
    let dict = PyDict::new(py);
    dict.set_item(field_name, errors).unwrap();
    dict.into()
}

fn wrap_err_dict(py: Python, field_name: &str, inner: Py<PyAny>) -> Py<PyAny> {
    if field_name.is_empty() {
        return inner;
    }
    let dict = PyDict::new(py);
    dict.set_item(field_name, inner).unwrap();
    dict.into()
}

fn wrap_err_dict_idx(py: Python, idx: usize, inner: Py<PyAny>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    dict.set_item(idx, inner).unwrap();
    dict.into()
}

fn err_dict_from_list(py: Python, field_name: &str, errors: Py<PyAny>) -> Py<PyAny> {
    if field_name.is_empty() {
        return errors;
    }
    let dict = PyDict::new(py);
    dict.set_item(field_name, errors).unwrap();
    dict.into()
}

fn format_item_errors_dict(py: Python, errors: &HashMap<usize, Py<PyAny>>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    for (idx, err_list) in errors.iter() {
        dict.set_item(*idx, err_list).unwrap();
    }
    dict.into()
}

/// Extracts the error value from a PyErr.
/// When we create `ValueError(dict_or_list)`, the dict/list is stored in args[0].
/// `e.value()` returns the exception object itself, so we need to extract args[0].
fn extract_error_value(py: Python, e: &PyErr) -> Py<PyAny> {
    e.value(py)
        .getattr("args")
        .and_then(|args| args.get_item(0))
        .map(|v| v.clone().unbind())
        .unwrap_or_else(|_| e.value(py).clone().into_any().unbind())
}

fn call_validator(py: Python, validator: &Py<PyAny>, value: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let result = validator.bind(py).call1((value,))?;
    if result.is_none() {
        return Ok(None);
    }
    Ok(Some(result.unbind()))
}

pub(crate) struct LoadContext<'a, 'py> {
    pub py: Python<'py>,
    pub post_loads: Option<&'a Bound<'py, PyDict>>,
}

pub(crate) fn deserialize_field_value<'py>(
    value: &Bound<'py, PyAny>,
    field: &FieldDescriptor,
    ctx: &LoadContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    // Any type accepts any value including None
    if field.field_type == FieldType::Any {
        return Ok(value.clone().unbind());
    }

    if value.is_none() {
        if !field.optional {
            let msg = field.none_error.as_deref().unwrap_or("Field may not be null.");
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                err_dict(ctx.py, &field.name, msg),
            ));
        }
        return Ok(ctx.py.None());
    }

    match field.field_type {
        FieldType::Str => {
            if let Ok(s) = value.cast::<PyString>() {
                if field.strip_whitespaces {
                    let trimmed = s.to_str()?.trim();
                    Ok(PyString::new(ctx.py, trimmed).into_any().unbind())
                } else {
                    Ok(value.clone().unbind())
                }
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid string.");
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ))
            }
        }
        FieldType::Int => {
            if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
                Ok(value.clone().unbind())
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid integer.");
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ))
            }
        }
        FieldType::Float => {
            let f: f64 = if value.is_instance_of::<PyFloat>() || (value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>()) {
                value.extract()?
            } else if let Ok(s) = value.extract::<&str>() {
                s.parse::<f64>().map_err(|_| {
                    let msg = field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(ctx.py, &field.name, msg))
                })?
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ));
            };
            if f.is_nan() || f.is_infinite() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, "Special numeric values (nan or infinity) are not permitted."),
                ));
            }
            Ok(f.into_pyobject(ctx.py)?.into_any().unbind())
        }
        FieldType::Bool => {
            if value.is_instance_of::<PyBool>() {
                Ok(value.clone().unbind())
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid boolean.");
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ))
            }
        }
        FieldType::Decimal => {
            let cached = get_cached_types(ctx.py)?;
            let decimal_cls = cached.decimal_cls.bind(ctx.py);

            let decimal_value = if value.is_instance(decimal_cls)? {
                value.clone()
            } else if let Ok(s) = value.cast::<PyString>() {
                match decimal_cls.call1((s,)) {
                    Ok(d) => d,
                    Err(_) => {
                        let msg = field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            err_dict(ctx.py, &field.name, msg),
                        ));
                    }
                }
            } else if (value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>()) || value.is_instance_of::<PyFloat>() {
                decimal_cls.call1((value.str()?.to_str()?,))?
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ));
            };

            if let Some(places) = field.decimal_places.filter(|&p| p >= 0) {
                let quantizer = match cached.get_quantizer(places) {
                    Some(q) => q.clone_ref(ctx.py),
                    None => {
                        let quantize_str = format!("1e-{}", places);
                        decimal_cls.call1((quantize_str,))?.unbind()
                    }
                };
                let quantized = if let Some(ref rounding) = field.decimal_rounding {
                    let kwargs = PyDict::new(ctx.py);
                    kwargs.set_item(cached.str_rounding.bind(ctx.py), rounding.bind(ctx.py))?;
                    decimal_value.call_method(cached.str_quantize.bind(ctx.py), (quantizer.bind(ctx.py),), Some(&kwargs))?
                } else {
                    decimal_value.call_method1(cached.str_quantize.bind(ctx.py), (quantizer.bind(ctx.py),))?
                };
                Ok(quantized.unbind())
            } else {
                Ok(decimal_value.unbind())
            }
        }
        FieldType::Uuid => {
            let cached = get_cached_types(ctx.py)?;
            let uuid_cls = cached.uuid_cls.bind(ctx.py);

            if value.is_instance(uuid_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                let s_str = s.to_str()?;
                match Uuid::parse_str(s_str) {
                    Ok(uuid) => cached.create_uuid_fast(ctx.py, uuid.as_u128()),
                    Err(_) => {
                        let msg = field.invalid_error.as_deref().unwrap_or("Not a valid UUID.");
                        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            err_dict(ctx.py, &field.name, msg),
                        ))
                    }
                }
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid UUID.");
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ))
            }
        }
        FieldType::DateTime => {
            let cached = get_cached_types(ctx.py)?;
            let datetime_cls = cached.datetime_cls.bind(ctx.py);

            if value.is_instance(datetime_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                let result = if let Some(ref fmt) = field.datetime_format {
                    datetime_cls.call_method1(cached.str_strptime.bind(ctx.py), (s, fmt.as_str()))
                } else {
                    datetime_cls.call_method1(cached.str_fromisoformat.bind(ctx.py), (s,))
                };
                match result {
                    Ok(dt) => {
                        let tzinfo = dt.getattr(cached.str_tzinfo.bind(ctx.py))?;
                        if tzinfo.is_none() {
                            let kwargs = PyDict::new(ctx.py);
                            kwargs.set_item(cached.str_tzinfo.bind(ctx.py), cached.utc_tz.bind(ctx.py))?;
                            Ok(dt.call_method(cached.str_replace.bind(ctx.py), (), Some(&kwargs))?.unbind())
                        } else {
                            Ok(dt.unbind())
                        }
                    }
                    Err(_) => {
                        let msg = field.invalid_error.as_deref().unwrap_or("Not a valid datetime.");
                        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            err_dict(ctx.py, &field.name, msg),
                        ))
                    }
                }
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid datetime.");
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ))
            }
        }
        FieldType::Date => {
            let cached = get_cached_types(ctx.py)?;
            let date_cls = cached.date_cls.bind(ctx.py);

            if value.is_instance(date_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                match date_cls.call_method1(cached.str_fromisoformat.bind(ctx.py), (s,)) {
                    Ok(d) => Ok(d.unbind()),
                    Err(_) => {
                        let msg = field.invalid_error.as_deref().unwrap_or("Not a valid date.");
                        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            err_dict(ctx.py, &field.name, msg),
                        ))
                    }
                }
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid date.");
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ))
            }
        }
        FieldType::Time => {
            let cached = get_cached_types(ctx.py)?;
            let time_cls = cached.time_cls.bind(ctx.py);

            if value.is_instance(time_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                match time_cls.call_method1(cached.str_fromisoformat.bind(ctx.py), (s,)) {
                    Ok(t) => Ok(t.unbind()),
                    Err(_) => {
                        let msg = field.invalid_error.as_deref().unwrap_or("Not a valid time.");
                        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            err_dict(ctx.py, &field.name, msg),
                        ))
                    }
                }
            } else {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid time.");
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict(ctx.py, &field.name, msg),
                ))
            }
        }
        FieldType::List => {
            let list = value.cast::<PyList>().map_err(|_| {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid list.");
                PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(ctx.py, &field.name, msg))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("List field missing item_schema")
            })?;

            let result = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item) in list.iter().enumerate() {
                match deserialize_field_value(&item, item_schema, ctx) {
                    Ok(v) => {
                        if let Some(ref item_validator) = field.item_validator {
                            if let Some(errors) = call_validator(ctx.py, item_validator, &v.bind(ctx.py))? {
                                item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                            }
                        }
                        result.append(v)?;
                    }
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(
                                ctx.py,
                                &field.name,
                                wrap_err_dict_idx(ctx.py, idx, inner),
                            ),
                        ));
                    }
                }
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            Ok(result.into_any().unbind())
        }
        FieldType::Set => {
            let list = value.cast::<PyList>().map_err(|_| {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid set.");
                PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(ctx.py, &field.name, msg))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Set field missing item_schema")
            })?;

            let items = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item) in list.iter().enumerate() {
                match deserialize_field_value(&item, item_schema, ctx) {
                    Ok(v) => {
                        if let Some(ref item_validator) = field.item_validator {
                            if let Some(errors) = call_validator(ctx.py, item_validator, &v.bind(ctx.py))? {
                                item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                            }
                        }
                        items.append(v)?;
                    }
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(
                                ctx.py,
                                &field.name,
                                wrap_err_dict_idx(ctx.py, idx, inner),
                            ),
                        ));
                    }
                }
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            let cached = get_cached_types(ctx.py)?;
            Ok(cached.set_cls.bind(ctx.py).call1((items,))?.unbind())
        }
        FieldType::FrozenSet => {
            let list = value.cast::<PyList>().map_err(|_| {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid frozenset.");
                PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(ctx.py, &field.name, msg))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("FrozenSet field missing item_schema")
            })?;

            let items = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item) in list.iter().enumerate() {
                match deserialize_field_value(&item, item_schema, ctx) {
                    Ok(v) => {
                        if let Some(ref item_validator) = field.item_validator {
                            if let Some(errors) = call_validator(ctx.py, item_validator, &v.bind(ctx.py))? {
                                item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                            }
                        }
                        items.append(v)?;
                    }
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(
                                ctx.py,
                                &field.name,
                                wrap_err_dict_idx(ctx.py, idx, inner),
                            ),
                        ));
                    }
                }
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            let cached = get_cached_types(ctx.py)?;
            Ok(cached.frozenset_cls.bind(ctx.py).call1((items,))?.unbind())
        }
        FieldType::Tuple => {
            let list = value.cast::<PyList>().map_err(|_| {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid tuple.");
                PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(ctx.py, &field.name, msg))
            })?;
            let item_schema = field.item_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Tuple field missing item_schema")
            })?;

            let items = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item) in list.iter().enumerate() {
                match deserialize_field_value(&item, item_schema, ctx) {
                    Ok(v) => {
                        if let Some(ref item_validator) = field.item_validator {
                            if let Some(errors) = call_validator(ctx.py, item_validator, &v.bind(ctx.py))? {
                                item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                            }
                        }
                        items.append(v)?;
                    }
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(
                                ctx.py,
                                &field.name,
                                wrap_err_dict_idx(ctx.py, idx, inner),
                            ),
                        ));
                    }
                }
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            let cached = get_cached_types(ctx.py)?;
            Ok(cached.tuple_cls.bind(ctx.py).call1((items,))?.unbind())
        }
        FieldType::Dict => {
            let dict = value.cast::<PyDict>().map_err(|_| {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid dict.");
                PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(ctx.py, &field.name, msg))
            })?;
            let value_schema = field.value_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Dict field missing value_schema")
            })?;

            let result = PyDict::new(ctx.py);
            for (k, v) in dict.iter() {
                let key_str: String = k.extract()?;
                match deserialize_field_value(&v, value_schema, ctx) {
                    Ok(val) => result.set_item(k, val)?,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(
                                ctx.py,
                                &field.name,
                                wrap_err_dict(ctx.py, &key_str, inner),
                            ),
                        ));
                    }
                }
            }
            Ok(result.into_any().unbind())
        }
        FieldType::Nested => {
            let dict = value.cast::<PyDict>().map_err(|_| {
                let msg = field.invalid_error.as_deref().unwrap_or("Not a valid object.");
                PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(ctx.py, &field.name, msg))
            })?;
            let nested_schema = field.nested_schema.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Nested field missing nested_schema")
            })?;

            match deserialize_dataclass(dict, nested_schema.cls.bind(ctx.py), &nested_schema.fields, &nested_schema.field_lookup, nested_schema.can_use_direct_slots, ctx) {
                Ok(obj) => Ok(obj),
                Err(e) => {
                    let inner = extract_error_value(ctx.py, &e);
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        wrap_err_dict(ctx.py, &field.name, inner),
                    ))
                }
            }
        }
        FieldType::StrEnum => {
            let values = field.str_enum_values.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("StrEnum field missing str_enum_values")
            })?;

            if let Ok(s) = value.cast::<PyString>() {
                let s_str = s.to_str()?;
                for (key, member) in values {
                    if key == s_str {
                        return Ok(member.clone_ref(ctx.py));
                    }
                }
            }

            let msg = field
                .invalid_error
                .as_deref()
                .map(|s| s.to_string())
                .unwrap_or_else(|| {
                    let allowed: Vec<_> = values.iter().map(|(k, _)| format!("'{}'", k)).collect();
                    format!("Not a valid choice: '{}'. Allowed values: [{}]", value, allowed.join(", "))
                });
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                err_dict(ctx.py, &field.name, &msg),
            ))
        }
        FieldType::IntEnum => {
            let values = field.int_enum_values.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("IntEnum field missing int_enum_values")
            })?;

            if let Ok(v) = value.extract::<i64>() {
                for (key, member) in values {
                    if *key == v {
                        return Ok(member.clone_ref(ctx.py));
                    }
                }
            }

            let msg = field
                .invalid_error
                .as_deref()
                .map(|s| s.to_string())
                .unwrap_or_else(|| {
                    let allowed: Vec<_> = values.iter().map(|(k, _)| k.to_string()).collect();
                    format!("Not a valid choice: '{}'. Allowed values: [{}]", value, allowed.join(", "))
                });
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                err_dict(ctx.py, &field.name, &msg),
            ))
        }
        FieldType::Union => {
            let variants = field.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Union field missing union_variants")
            })?;

            for variant in variants.iter() {
                if let Ok(result) = deserialize_field_value(value, variant, ctx) {
                    return Ok(result);
                }
            }

            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Value does not match any union variant for field '{}'",
                field.name
            )))
        }
        FieldType::Any => Ok(value.clone().unbind()),
    }
}

fn deserialize_dataclass<'py>(
    dict: &Bound<'py, PyDict>,
    cls: &Bound<'py, PyAny>,
    fields: &[FieldDescriptor],
    field_lookup: &HashMap<String, usize>,
    can_use_direct_slots: bool,
    ctx: &LoadContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    if can_use_direct_slots {
        deserialize_dataclass_direct_slots(dict, cls, fields, field_lookup, ctx)
    } else {
        deserialize_dataclass_kwargs(dict, cls, fields, field_lookup, ctx)
    }
}

fn deserialize_dataclass_kwargs<'py>(
    dict: &Bound<'py, PyDict>,
    cls: &Bound<'py, PyAny>,
    fields: &[FieldDescriptor],
    field_lookup: &HashMap<String, usize>,
    ctx: &LoadContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    let kwargs = PyDict::new(ctx.py);
    let mut seen_fields = vec![false; fields.len()];

    for (key, value) in dict.iter() {
        let key_str: String = key.extract()?;
        if let Some(&idx) = field_lookup.get(&key_str) {
            let field = &fields[idx];
            seen_fields[idx] = true;
            if !field.field_init {
                continue;
            }
            let mut deserialized = deserialize_field_value(&value, field, ctx)?;

            if let Some(pl) = ctx.post_loads {
                if let Ok(Some(post_load_fn)) = pl.get_item(&field.name) {
                    if !post_load_fn.is_none() {
                        deserialized = post_load_fn.call1((deserialized,))?.unbind();
                    }
                }
            }

            if let Some(ref validator) = field.validator {
                if let Some(errors) = call_validator(ctx.py, validator, &deserialized.bind(ctx.py))? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        err_dict_from_list(ctx.py, &field.name, errors),
                    ));
                }
            }

            kwargs.set_item(field.name_interned.bind(ctx.py), deserialized)?;
        }
    }

    for (idx, field) in fields.iter().enumerate() {
        if !seen_fields[idx] {
            if !field.field_init {
                continue;
            }
            if let Some(ref default_factory) = field.default_factory {
                let value = default_factory.call0(ctx.py)?;
                kwargs.set_item(field.name_interned.bind(ctx.py), value)?;
            } else if let Some(ref default_value) = field.default_value {
                kwargs.set_item(field.name_interned.bind(ctx.py), default_value.clone_ref(ctx.py))?;
            } else if field.optional {
                kwargs.set_item(field.name_interned.bind(ctx.py), ctx.py.None())?;
            } else {
                let msg = field
                    .required_error
                    .as_deref()
                    .unwrap_or("Missing data for required field.");
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(
                    ctx.py,
                    &field.name,
                    msg,
                )));
            }
        }
    }

    cls.call((), Some(&kwargs))
        .map(|o| o.unbind())
}

fn deserialize_dataclass_direct_slots<'py>(
    dict: &Bound<'py, PyDict>,
    cls: &Bound<'py, PyAny>,
    fields: &[FieldDescriptor],
    field_lookup: &HashMap<String, usize>,
    ctx: &LoadContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    let cached_types = get_cached_types(ctx.py)?;
    let object_type = cached_types.object_cls.bind(ctx.py);
    let instance = object_type.call_method1(cached_types.str_new.bind(ctx.py), (cls,))?;

    let mut field_values: Vec<Option<Py<PyAny>>> = (0..fields.len()).map(|_| None).collect();

    for (key, value) in dict.iter() {
        let key_str: String = key.extract()?;
        if let Some(&idx) = field_lookup.get(&key_str) {
            let field = &fields[idx];
            let mut deserialized = deserialize_field_value(&value, field, ctx)?;

            if let Some(pl) = ctx.post_loads {
                if let Ok(Some(post_load_fn)) = pl.get_item(&field.name) {
                    if !post_load_fn.is_none() {
                        deserialized = post_load_fn.call1((deserialized,))?.unbind();
                    }
                }
            }

            if let Some(ref validator) = field.validator {
                if let Some(errors) = call_validator(ctx.py, validator, &deserialized.bind(ctx.py))? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        err_dict_from_list(ctx.py, &field.name, errors),
                    ));
                }
            }

            field_values[idx] = Some(deserialized);
        }
    }

    for (idx, field) in fields.iter().enumerate() {
        let py_value = if let Some(value) = field_values[idx].take() {
            value
        } else if let Some(ref default_factory) = field.default_factory {
            default_factory.call0(ctx.py)?
        } else if let Some(ref default_value) = field.default_value {
            default_value.clone_ref(ctx.py)
        } else if field.optional {
            ctx.py.None()
        } else {
            let msg = field
                .required_error
                .as_deref()
                .unwrap_or("Missing data for required field.");
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(err_dict(
                ctx.py,
                &field.name,
                msg,
            )));
        };

        if let Some(offset) = field.slot_offset {
            unsafe {
                set_slot_value_direct(&instance, offset, py_value);
            }
        } else {
            instance.setattr(field.name_interned.bind(ctx.py), py_value)?;
        }
    }

    Ok(instance.unbind())
}

pub(crate) fn deserialize_root_type<'py>(
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    ctx: &LoadContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    match descriptor.type_kind {
        TypeKind::Dataclass => {
            let dict = value.cast::<PyDict>().map_err(|_| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a dict for dataclass")
            })?;
            let cls = descriptor.cls.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing cls for dataclass")
            })?;
            deserialize_dataclass(
                dict,
                cls.bind(ctx.py),
                &descriptor.fields,
                &descriptor.field_lookup,
                descriptor.can_use_direct_slots,
                ctx,
            )
        }
        TypeKind::Primitive => {
            let field_type = descriptor.primitive_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_type")
            })?;
            deserialize_primitive(value, field_type, ctx)
        }
        TypeKind::List => {
            let list = value.cast::<PyList>().map_err(|_| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a list")
            })?;
            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for list")
            })?;

            let result = PyList::empty(ctx.py);
            for (idx, item) in list.iter().enumerate() {
                match deserialize_root_type(&item, item_descriptor, ctx) {
                    Ok(v) => result.append(v)?,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict_idx(ctx.py, idx, inner),
                        ));
                    }
                }
            }
            Ok(result.into_any().unbind())
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
                let key_str: String = k.extract()?;
                match deserialize_root_type(&v, value_descriptor, ctx) {
                    Ok(val) => result.set_item(k, val)?,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(ctx.py, &key_str, inner),
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
                deserialize_root_type(value, inner_descriptor, ctx)
            }
        }
        TypeKind::Set => {
            // Reject strings - they're iterable but not valid sets
            if value.is_instance_of::<PyString>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid set.",
                ));
            }

            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for set")
            })?;

            let items = PyList::empty(ctx.py);
            for (idx, item) in value.try_iter()?.enumerate() {
                let item = item?;
                match deserialize_root_type(&item, item_descriptor, ctx) {
                    Ok(v) => items.append(v)?,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict_idx(ctx.py, idx, inner),
                        ));
                    }
                }
            }
            let cached = get_cached_types(ctx.py)?;
            Ok(cached.set_cls.bind(ctx.py).call1((items,))?.unbind())
        }
        TypeKind::FrozenSet => {
            // Reject strings - they're iterable but not valid frozensets
            if value.is_instance_of::<PyString>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid frozenset.",
                ));
            }

            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for frozenset")
            })?;

            let items = PyList::empty(ctx.py);
            for (idx, item) in value.try_iter()?.enumerate() {
                let item = item?;
                match deserialize_root_type(&item, item_descriptor, ctx) {
                    Ok(v) => items.append(v)?,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict_idx(ctx.py, idx, inner),
                        ));
                    }
                }
            }
            let cached = get_cached_types(ctx.py)?;
            Ok(cached.frozenset_cls.bind(ctx.py).call1((items,))?.unbind())
        }
        TypeKind::Tuple => {
            // Reject strings - they're iterable but not valid tuples
            if value.is_instance_of::<PyString>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid tuple.",
                ));
            }

            let item_descriptor = descriptor.item_type.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for tuple")
            })?;

            let items = PyList::empty(ctx.py);
            for (idx, item) in value.try_iter()?.enumerate() {
                let item = item?;
                match deserialize_root_type(&item, item_descriptor, ctx) {
                    Ok(v) => items.append(v)?,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict_idx(ctx.py, idx, inner),
                        ));
                    }
                }
            }
            let cached = get_cached_types(ctx.py)?;
            Ok(cached.tuple_cls.bind(ctx.py).call1((items,))?.unbind())
        }
        TypeKind::Union => {
            let variants = descriptor.union_variants.as_ref().ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union")
            })?;

            for variant in variants.iter() {
                if let Ok(result) = deserialize_root_type(value, variant, ctx) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value does not match any union variant",
            ))
        }
    }
}

fn deserialize_primitive<'py>(
    value: &Bound<'py, PyAny>,
    field_type: &FieldType,
    ctx: &LoadContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    if value.is_none() {
        return Ok(ctx.py.None());
    }

    match field_type {
        FieldType::Str | FieldType::Int | FieldType::Bool => Ok(value.clone().unbind()),
        FieldType::Float => {
            let f: f64 = value.extract()?;
            Ok(f.into_pyobject(ctx.py)?.into_any().unbind())
        }
        FieldType::Decimal => {
            let cached = get_cached_types(ctx.py)?;
            let decimal_cls = cached.decimal_cls.bind(ctx.py);
            if value.is_instance(decimal_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                Ok(decimal_cls.call1((s,))?.unbind())
            } else {
                Ok(decimal_cls.call1((value.str()?.to_str()?,))?.unbind())
            }
        }
        FieldType::Uuid => {
            let cached = get_cached_types(ctx.py)?;
            let uuid_cls = cached.uuid_cls.bind(ctx.py);
            if value.is_instance(uuid_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                let s_str = s.to_str()?;
                match Uuid::parse_str(s_str) {
                    Ok(uuid) => cached.create_uuid_fast(ctx.py, uuid.as_u128()),
                    Err(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        "Not a valid UUID",
                    )),
                }
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid UUID",
                ))
            }
        }
        FieldType::DateTime => {
            let cached = get_cached_types(ctx.py)?;
            let datetime_cls = cached.datetime_cls.bind(ctx.py);
            if value.is_instance(datetime_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                Ok(datetime_cls.call_method1(cached.str_fromisoformat.bind(ctx.py), (s,))?.unbind())
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid datetime",
                ))
            }
        }
        FieldType::Date => {
            let cached = get_cached_types(ctx.py)?;
            let date_cls = cached.date_cls.bind(ctx.py);
            if value.is_instance(date_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                Ok(date_cls.call_method1(cached.str_fromisoformat.bind(ctx.py), (s,))?.unbind())
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid date",
                ))
            }
        }
        FieldType::Time => {
            let cached = get_cached_types(ctx.py)?;
            let time_cls = cached.time_cls.bind(ctx.py);
            if value.is_instance(time_cls)? {
                Ok(value.clone().unbind())
            } else if let Ok(s) = value.cast::<PyString>() {
                Ok(time_cls.call_method1(cached.str_fromisoformat.bind(ctx.py), (s,))?.unbind())
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid time",
                ))
            }
        }
        FieldType::Any => Ok(value.clone().unbind()),
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unsupported primitive type",
        )),
    }
}

pub fn load<'py>(
    py: Python<'py>,
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    post_loads: Option<&Bound<'py, PyDict>>,
) -> PyResult<Py<PyAny>> {
    let ctx = LoadContext { py, post_loads };

    deserialize_root_type(value, descriptor, &ctx)
}
