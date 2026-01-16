use std::collections::HashMap;
use std::fmt::Write;

use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDate, PyDateAccess, PyDateTime, PyDelta, PyDeltaAccess, PyDict, PyFloat, PyFrozenSet, PyInt, PyList, PySet, PyString, PyTime, PyTimeAccess, PyTuple, PyTzInfoAccess};
use rust_decimal::Decimal;
use rust_decimal::prelude::FromStr;
use rust_decimal::RoundingStrategy;

use crate::cache::get_cached_types;
use crate::slots::get_slot_value_direct;
use crate::types::{DecimalPlaces, FieldDescriptor, FieldType, TypeDescriptor, TypeKind};

#[inline]
fn format_datetime_to_buf(buf: &mut arrayvec::ArrayString<32>, dt: &Bound<'_, PyDateTime>, offset_seconds: Option<i32>) {
    let micros = dt.get_microsecond();
    if micros == 0 {
        write!(buf, "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}",
            dt.get_year(), dt.get_month(), dt.get_day(),
            dt.get_hour(), dt.get_minute(), dt.get_second()).unwrap();
    } else {
        write!(buf, "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:06}",
            dt.get_year(), dt.get_month(), dt.get_day(),
            dt.get_hour(), dt.get_minute(), dt.get_second(), micros).unwrap();
    }
    if let Some(offset_secs) = offset_seconds {
        if offset_secs >= 0 {
            write!(buf, "+{:02}:{:02}", offset_secs / 3600, (offset_secs % 3600) / 60).unwrap();
        } else {
            let abs_secs = offset_secs.abs();
            write!(buf, "-{:02}:{:02}", abs_secs / 3600, (abs_secs % 3600) / 60).unwrap();
        }
    }
}

#[inline]
fn format_date_to_buf(buf: &mut arrayvec::ArrayString<10>, year: i32, month: u8, day: u8) {
    write!(buf, "{year:04}-{month:02}-{day:02}").unwrap();
}

#[inline]
fn format_time_to_buf(buf: &mut arrayvec::ArrayString<21>, t: &Bound<'_, PyTime>, offset_seconds: Option<i32>) {
    let micros = t.get_microsecond();
    if micros == 0 {
        write!(buf, "{:02}:{:02}:{:02}", t.get_hour(), t.get_minute(), t.get_second()).unwrap();
    } else {
        write!(buf, "{:02}:{:02}:{:02}.{:06}", t.get_hour(), t.get_minute(), t.get_second(), micros).unwrap();
    }
    if let Some(offset_secs) = offset_seconds {
        if offset_secs >= 0 {
            write!(buf, "+{:02}:{:02}", offset_secs / 3600, (offset_secs % 3600) / 60).unwrap();
        } else {
            let abs_secs = offset_secs.abs();
            write!(buf, "-{:02}:{:02}", abs_secs / 3600, (abs_secs % 3600) / 60).unwrap();
        }
    }
}

#[inline]
fn get_tz_offset_seconds(py: Python, tz: &Bound<'_, pyo3::types::PyTzInfo>, reference: &Bound<'_, PyAny>) -> PyResult<i32> {
    let cached = get_cached_types(py)?;
    if tz.is(cached.utc_tz.bind(py)) {
        return Ok(0);
    }
    let offset = tz.call_method1(cached.str_utcoffset.bind(py), (reference,))?;
    if let Ok(delta) = offset.cast::<PyDelta>() {
        Ok(delta.get_days() * 86400 + delta.get_seconds())
    } else {
        Ok(0)
    }
}

#[inline]
fn python_rounding_to_rust(rounding: Option<&Py<PyAny>>, py: Python) -> RoundingStrategy {
    let Some(rounding) = rounding else {
        return RoundingStrategy::MidpointNearestEven;
    };
    let Ok(s) = rounding.bind(py).extract::<&str>() else {
        return RoundingStrategy::MidpointNearestEven;
    };
    match s {
        "ROUND_UP" => RoundingStrategy::AwayFromZero,
        "ROUND_DOWN" => RoundingStrategy::ToZero,
        "ROUND_CEILING" => RoundingStrategy::ToPositiveInfinity,
        "ROUND_FLOOR" => RoundingStrategy::ToNegativeInfinity,
        "ROUND_HALF_UP" => RoundingStrategy::MidpointAwayFromZero,
        "ROUND_HALF_DOWN" => RoundingStrategy::MidpointTowardZero,
        "ROUND_05UP" => panic!("ROUND_05UP is not supported in nuked implementation"),
        _ => RoundingStrategy::MidpointNearestEven,
    }
}

pub struct DictContext<'a, 'py> {
    pub py: Python<'py>,
    pub none_value_handling: Option<&'a str>,
    pub global_decimal_places: Option<i32>,
}

fn err_dict_from_list(py: Python, field_name: &str, errors: Py<PyAny>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    dict.set_item(field_name, errors).unwrap();
    dict.into()
}

fn wrap_err_dict(py: Python, field_name: &str, inner: Py<PyAny>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    dict.set_item(field_name, inner).unwrap();
    dict.into()
}

fn format_item_errors_dict(py: Python, errors: &HashMap<usize, Py<PyAny>>) -> Py<PyAny> {
    let dict = PyDict::new(py);
    for (idx, err_list) in errors {
        dict.set_item(*idx, err_list).unwrap();
    }
    dict.into()
}

fn call_validator(py: Python, validator: &Py<PyAny>, value: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let result = validator.bind(py).call1((value,))?;
    if result.is_none() {
        return Ok(None);
    }
    Ok(Some(result.unbind()))
}

fn serialize_any_value<'py>(
    value: &Bound<'py, PyAny>,
    py: Python<'py>,
    field_name: Option<&str>,
) -> PyResult<Py<PyAny>> {
    if value.is_none() {
        return Ok(py.None());
    }
    if value.is_instance_of::<PyBool>()
        || value.is_instance_of::<PyInt>()
        || value.is_instance_of::<PyFloat>()
        || value.is_instance_of::<PyString>()
    {
        return Ok(value.clone().unbind());
    }
    if let Ok(list) = value.cast::<PyList>() {
        let result = PyList::empty(py);
        for item in list.iter() {
            result.append(serialize_any_value(&item, py, field_name)?)?;
        }
        return Ok(result.into_any().unbind());
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let result = PyDict::new(py);
        for (k, v) in dict.iter() {
            if !k.is_instance_of::<PyString>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    match field_name {
                        Some(name) => format!(
                            "{{\"{name}\": [\"Not a valid JSON-serializable value.\"]}}"
                        ),
                        None => "Any field dict keys must be strings".to_string(),
                    },
                ));
            }
            result.set_item(k, serialize_any_value(&v, py, field_name)?)?;
        }
        return Ok(result.into_any().unbind());
    }
    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
        match field_name {
            Some(name) => format!(
                "{{\"{name}\": [\"Not a valid JSON-serializable value.\"]}}"
            ),
            None => format!(
                "Any field value must be JSON-serializable (str/int/float/bool/None/list/dict), got: {}",
                value.get_type().name()?
            ),
        },
    ))
}

#[allow(clippy::too_many_lines)]
fn serialize_field_value<'py>(
    value: &Bound<'py, PyAny>,
    field: &FieldDescriptor,
    ctx: &DictContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    if value.is_none() {
        return Ok(ctx.py.None());
    }

    match field.field_type {
        FieldType::Str => {
            if !value.is_instance_of::<PyString>() {
                let errors = PyList::new(ctx.py, ["Not a valid string."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            if field.strip_whitespaces {
                let s: String = value.extract()?;
                Ok(PyString::new(ctx.py, s.trim()).into_any().unbind())
            } else {
                Ok(value.clone().unbind())
            }
        }
        FieldType::Int => {
            if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
                let errors = PyList::new(ctx.py, ["Not a valid integer."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            Ok(value.clone().unbind())
        }
        FieldType::Bool => {
            if !value.is_instance_of::<PyBool>() {
                let errors = PyList::new(ctx.py, ["Not a valid boolean."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            Ok(value.clone().unbind())
        }
        FieldType::Float => {
            if value.is_instance_of::<PyBool>() {
                let errors = PyList::new(ctx.py, ["Not a valid number."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            if value.is_instance_of::<PyInt>() {
                Ok(value.clone().unbind())
            } else if value.is_instance_of::<PyFloat>() {
                let f: f64 = value.extract()?;
                if f.is_nan() || f.is_infinite() {
                    let errors = PyList::new(ctx.py, ["Special numeric values (nan or infinity) are not permitted."])?;
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                    ));
                }
                Ok(value.clone().unbind())
            } else {
                let errors = PyList::new(ctx.py, ["Not a valid number."])?;
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ))
            }
        }
        FieldType::Decimal => {
            let cached = get_cached_types(ctx.py)?;
            if !value.is_instance(cached.decimal_cls.bind(ctx.py))? {
                let errors = PyList::new(ctx.py, ["Not a valid decimal."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }

            let decimal_places = match field.decimal_places {
                DecimalPlaces::NoRounding => None,
                DecimalPlaces::Places(n) => Some(n),
                DecimalPlaces::NotSpecified => ctx.global_decimal_places.or(Some(2)),
            };

            let format_result = value.call_method1("__format__", ("f",))?;
            let formatted = format_result.cast::<PyString>()?;
            let decimal_str = formatted.to_str()?;

            if let Some(places) = decimal_places.filter(|&p| p >= 0) {
                if field.decimal_rounding.is_some() {
                    if let Ok(mut rust_decimal) = Decimal::from_str(decimal_str) {
                        let strategy = python_rounding_to_rust(field.decimal_rounding.as_ref(), ctx.py);
                        rust_decimal = rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy);
                        let rounded = format!("{:.prec$}", rust_decimal, prec = places.cast_unsigned() as usize);
                        return Ok(PyString::new(ctx.py, &rounded).into_any().unbind());
                    }
                } else if let Ok(rust_decimal) = Decimal::from_str(decimal_str) {
                    let normalized = rust_decimal.normalize();
                    let scale = normalized.scale();
                    if scale > places.cast_unsigned() {
                        let msg = field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                        let errors = PyList::new(ctx.py, [msg])?;
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                        ));
                    }
                }
            }

            Ok(format_result.unbind())
        }
        FieldType::Uuid => {
            let cached = get_cached_types(ctx.py)?;
            if !value.is_instance(cached.uuid_cls.bind(ctx.py))? {
                let errors = PyList::new(ctx.py, ["Not a valid UUID."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let uuid_int: u128 = value.getattr(cached.str_int.bind(ctx.py))?.extract()?;
            let uuid = uuid::Uuid::from_u128(uuid_int);
            let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
            let s = uuid.hyphenated().encode_lower(&mut buf);
            Ok(PyString::new(ctx.py, s).into_any().unbind())
        }
        FieldType::DateTime => {
            if !value.is_instance_of::<PyDateTime>() {
                let errors = PyList::new(ctx.py, ["Not a valid datetime."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let dt: &Bound<'_, PyDateTime> = value.cast()?;
            if let Some(ref fmt) = field.datetime_format {
                let cached = get_cached_types(ctx.py)?;
                let s: String = dt.call_method1(cached.str_strftime.bind(ctx.py), (fmt.as_str(),))?.extract()?;
                Ok(PyString::new(ctx.py, &s).into_any().unbind())
            } else {
                let offset_seconds = dt.get_tzinfo()
                    .map(|tz| get_tz_offset_seconds(ctx.py, &tz, dt.as_any()))
                    .transpose()?;
                let mut buf = arrayvec::ArrayString::<32>::new();
                format_datetime_to_buf(&mut buf, dt, offset_seconds);
                Ok(PyString::new(ctx.py, &buf).into_any().unbind())
            }
        }
        FieldType::Date => {
            if !value.is_instance_of::<PyDate>() {
                let errors = PyList::new(ctx.py, ["Not a valid date."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let d: &Bound<'_, PyDate> = value.cast()?;
            let mut buf = arrayvec::ArrayString::<10>::new();
            format_date_to_buf(&mut buf, d.get_year(), d.get_month(), d.get_day());
            Ok(PyString::new(ctx.py, &buf).into_any().unbind())
        }
        FieldType::Time => {
            if !value.is_instance_of::<PyTime>() {
                let errors = PyList::new(ctx.py, ["Not a valid time."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let t: &Bound<'_, PyTime> = value.cast()?;
            let offset_seconds = t.get_tzinfo()
                .map(|tz| get_tz_offset_seconds(ctx.py, &tz, &ctx.py.None().into_bound(ctx.py)))
                .transpose()?;
            let mut buf = arrayvec::ArrayString::<21>::new();
            format_time_to_buf(&mut buf, t, offset_seconds);
            Ok(PyString::new(ctx.py, &buf).into_any().unbind())
        }
        FieldType::List => {
            if !value.is_instance_of::<PyList>() {
                let errors = PyList::new(ctx.py, ["Not a valid list."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let list = value.cast::<PyList>()?;
            let item_schema = field
                .item_schema
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("List field missing item_schema"))?;

            let result = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item) in list.iter().enumerate() {
                if let Some(ref item_validator) = field.item_validator {
                    if let Some(errors) = call_validator(ctx.py, item_validator, &item)? {
                        item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                    }
                }
                let item_value = serialize_field_value(&item, item_schema, ctx)?;
                result.append(item_value)?;
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            Ok(result.into_any().unbind())
        }
        FieldType::Dict => {
            if !value.is_instance_of::<PyDict>() {
                let errors = PyList::new(ctx.py, ["Not a valid mapping."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let dict = value.cast::<PyDict>()?;
            let value_schema = field
                .value_schema
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Dict field missing value_schema"))?;

            let result = PyDict::new(ctx.py);
            let mut value_errors: Option<Py<PyAny>> = None;
            for (k, v) in dict.iter() {
                if let Some(ref value_validator) = field.value_validator {
                    if let Some(errors) = call_validator(ctx.py, value_validator, &v)? {
                        let err_dict = value_errors.get_or_insert_with(|| PyDict::new(ctx.py).into_any().unbind());
                        err_dict.bind(ctx.py).cast::<PyDict>()?.set_item(&k, errors)?;
                    }
                }
                let serialized_value = serialize_field_value(&v, value_schema, ctx)?;
                result.set_item(k, serialized_value)?;
            }
            if let Some(ref errs) = value_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, errs.clone_ref(ctx.py)),
                ));
            }
            Ok(result.into_any().unbind())
        }
        FieldType::Nested => {
            let nested_schema = field
                .nested_schema
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Nested field missing nested_schema"))?;
            if !value.is_instance(nested_schema.cls.bind(ctx.py))? {
                let errors = PyList::new(ctx.py, ["Not a valid nested object."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            serialize_dataclass(value, &nested_schema.fields, ctx)
        }
        FieldType::StrEnum => {
            if let Some(ref enum_cls) = field.enum_cls {
                if !value.is_instance(enum_cls.bind(ctx.py))? {
                    let value_type_name: String = value.get_type().name()?.extract()?;
                    let enum_name = field.enum_name.as_deref().unwrap_or("Enum");
                    let members_repr = field.enum_members_repr.as_deref().unwrap_or("[]");
                    let error_msg = format!(
                        "Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}"
                    );
                    let errors = PyList::new(ctx.py, &[error_msg])?;
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        errors.into_any().unbind(),
                    ));
                }
            }
            Ok(value.cast::<PyString>()?.to_owned().into_any().unbind())
        }
        FieldType::IntEnum => {
            if let Some(ref enum_cls) = field.enum_cls {
                if !value.is_instance(enum_cls.bind(ctx.py))? {
                    let value_type_name: String = value.get_type().name()?.extract()?;
                    let enum_name = field.enum_name.as_deref().unwrap_or("Enum");
                    let members_repr = field.enum_members_repr.as_deref().unwrap_or("[]");
                    let error_msg = format!(
                        "Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}"
                    );
                    let errors = PyList::new(ctx.py, &[error_msg])?;
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        errors.into_any().unbind(),
                    ));
                }
            }
            Ok(value.cast::<PyInt>()?.to_owned().into_any().unbind())
        }
        FieldType::Set => {
            if !value.is_instance_of::<PySet>() {
                let errors = PyList::new(ctx.py, ["Not a valid set."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let iter = value.try_iter()?;
            let item_schema = field
                .item_schema
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Set field missing item_schema"))?;

            let result = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item_result) in iter.enumerate() {
                let item = item_result?;
                if let Some(ref item_validator) = field.item_validator {
                    if let Some(errors) = call_validator(ctx.py, item_validator, &item)? {
                        item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                    }
                }
                let item_value = serialize_field_value(&item, item_schema, ctx)?;
                result.append(item_value)?;
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            Ok(result.into_any().unbind())
        }
        FieldType::FrozenSet => {
            if !value.is_instance_of::<PyFrozenSet>() {
                let errors = PyList::new(ctx.py, ["Not a valid frozenset."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let iter = value.try_iter()?;
            let item_schema = field
                .item_schema
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("FrozenSet field missing item_schema"))?;

            let result = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item_result) in iter.enumerate() {
                let item = item_result?;
                if let Some(ref item_validator) = field.item_validator {
                    if let Some(errors) = call_validator(ctx.py, item_validator, &item)? {
                        item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                    }
                }
                let item_value = serialize_field_value(&item, item_schema, ctx)?;
                result.append(item_value)?;
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            Ok(result.into_any().unbind())
        }
        FieldType::Tuple => {
            if !value.is_instance_of::<PyTuple>() {
                let errors = PyList::new(ctx.py, ["Not a valid tuple."])?;
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors.into_any().unbind()),
                ));
            }
            let iter = value.try_iter()?;
            let item_schema = field
                .item_schema
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Tuple field missing item_schema"))?;

            let result = PyList::empty(ctx.py);
            let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
            for (idx, item_result) in iter.enumerate() {
                let item = item_result?;
                if let Some(ref item_validator) = field.item_validator {
                    if let Some(errors) = call_validator(ctx.py, item_validator, &item)? {
                        item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                    }
                }
                let item_value = serialize_field_value(&item, item_schema, ctx)?;
                result.append(item_value)?;
            }
            if let Some(ref errs) = item_errors {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    wrap_err_dict(ctx.py, &field.name, format_item_errors_dict(ctx.py, errs)),
                ));
            }
            Ok(result.into_any().unbind())
        }
        FieldType::Union => {
            let variants = field
                .union_variants
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Union field missing union_variants"))?;

            for variant in variants {
                if let Ok(result) = serialize_field_value(value, variant, ctx) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Value does not match any union variant for field '{}'",
                field.name
            )))
        }
        FieldType::Any => serialize_any_value(value, ctx.py, Some(&field.name)),
    }
}

fn serialize_dataclass<'py>(
    obj: &Bound<'py, PyAny>,
    fields: &[FieldDescriptor],
    ctx: &DictContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    let ignore_none = ctx
        .none_value_handling
        .is_none_or(|s| s == "ignore");

    let cached = get_cached_types(ctx.py)?;
    let missing_sentinel = cached.missing_sentinel.bind(ctx.py);
    let result = PyDict::new(ctx.py);

    for field in fields {
        let py_value = match field.slot_offset {
            Some(offset) => match unsafe { get_slot_value_direct(ctx.py, obj, offset) } {
                Some(value) => value,
                None => obj.getattr(field.name.as_str())?,
            },
            None => obj.getattr(field.name.as_str())?,
        };

        if py_value.is(missing_sentinel) || (py_value.is_none() && ignore_none) {
            continue;
        }

        if let Some(ref validator) = field.validator {
            if let Some(errors) = call_validator(ctx.py, validator, &py_value)? {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    err_dict_from_list(ctx.py, &field.name, errors),
                ));
            }
        }

        let key = field.serialized_name.as_ref().unwrap_or(&field.name);
        let serialized_value = serialize_field_value(&py_value, field, ctx)?;
        result.set_item(key.as_str(), serialized_value)?;
    }

    Ok(result.into_any().unbind())
}

fn serialize_root_type<'py>(
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    ctx: &DictContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    match descriptor.type_kind {
        TypeKind::Dataclass => serialize_dataclass(value, &descriptor.fields, ctx),
        TypeKind::Primitive => {
            let field_type = descriptor
                .primitive_type
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing primitive_type"))?;
            serialize_primitive(value, field_type, ctx)
        }
        TypeKind::List => {
            let list = value.cast::<PyList>()?;
            let item_descriptor = descriptor
                .item_type
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for list"))?;

            let result = PyList::empty(ctx.py);
            for item in list.iter() {
                let item_value = serialize_root_type(&item, item_descriptor, ctx)?;
                result.append(item_value)?;
            }
            Ok(result.into_any().unbind())
        }
        TypeKind::Dict => {
            let dict = value.cast::<PyDict>()?;
            let value_descriptor = descriptor
                .value_type
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing value_type for dict"))?;

            let result = PyDict::new(ctx.py);
            for (k, v) in dict.iter() {
                let serialized_value = serialize_root_type(&v, value_descriptor, ctx)?;
                result.set_item(k, serialized_value)?;
            }
            Ok(result.into_any().unbind())
        }
        TypeKind::Optional => {
            if value.is_none() {
                Ok(ctx.py.None())
            } else {
                let inner_descriptor = descriptor
                    .inner_type
                    .as_ref()
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing inner_type for optional"))?;
                serialize_root_type(value, inner_descriptor, ctx)
            }
        }
        TypeKind::Set | TypeKind::FrozenSet | TypeKind::Tuple => {
            let iter = value.try_iter()?;
            let item_descriptor = descriptor
                .item_type
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing item_type for collection"))?;

            let result = PyList::empty(ctx.py);
            for item_result in iter {
                let item = item_result?;
                let item_value = serialize_root_type(&item, item_descriptor, ctx)?;
                result.append(item_value)?;
            }
            Ok(result.into_any().unbind())
        }
        TypeKind::Union => {
            let variants = descriptor
                .union_variants
                .as_ref()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing union_variants for union"))?;

            for variant in variants {
                if let Ok(result) = serialize_root_type(value, variant, ctx) {
                    return Ok(result);
                }
            }
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Value does not match any union variant",
            ))
        }
    }
}

#[allow(clippy::too_many_lines)]
fn serialize_primitive<'py>(
    value: &Bound<'py, PyAny>,
    field_type: &FieldType,
    ctx: &DictContext<'_, 'py>,
) -> PyResult<Py<PyAny>> {
    if value.is_none() {
        return Ok(ctx.py.None());
    }

    match field_type {
        FieldType::Str => {
            if !value.is_instance_of::<PyString>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid string.",
                ));
            }
            Ok(value.clone().unbind())
        }
        FieldType::Int => {
            if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid integer.",
                ));
            }
            Ok(value.clone().unbind())
        }
        FieldType::Bool => {
            if !value.is_instance_of::<PyBool>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid boolean.",
                ));
            }
            Ok(value.clone().unbind())
        }
        FieldType::Float => {
            if value.is_instance_of::<PyBool>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid number.",
                ));
            }
            if value.is_instance_of::<PyInt>() {
                Ok(value.clone().unbind())
            } else if value.is_instance_of::<PyFloat>() {
                let f: f64 = value.extract()?;
                if f.is_nan() || f.is_infinite() {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        "Cannot serialize NaN/Infinite float",
                    ));
                }
                Ok(value.clone().unbind())
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid number.",
                ))
            }
        }
        FieldType::Decimal => {
            let cached = get_cached_types(ctx.py)?;
            if !value.is_instance(cached.decimal_cls.bind(ctx.py))? {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid decimal.",
                ));
            }
            let format_result = value.call_method1("__format__", ("f",))?;
            Ok(format_result.unbind())
        }
        FieldType::Uuid => {
            let cached = get_cached_types(ctx.py)?;
            if !value.is_instance(cached.uuid_cls.bind(ctx.py))? {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid UUID.",
                ));
            }
            let uuid_int: u128 = value.getattr(cached.str_int.bind(ctx.py))?.extract()?;
            let uuid = uuid::Uuid::from_u128(uuid_int);
            let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
            let s = uuid.hyphenated().encode_lower(&mut buf);
            Ok(PyString::new(ctx.py, s).into_any().unbind())
        }
        FieldType::DateTime => {
            if !value.is_instance_of::<PyDateTime>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid datetime.",
                ));
            }
            let cached = get_cached_types(ctx.py)?;
            let s: String = value.call_method0(cached.str_isoformat.bind(ctx.py))?.extract()?;
            Ok(PyString::new(ctx.py, &s).into_any().unbind())
        }
        FieldType::Date => {
            if !value.is_instance_of::<PyDate>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid date.",
                ));
            }
            let cached = get_cached_types(ctx.py)?;
            let s: String = value.call_method0(cached.str_isoformat.bind(ctx.py))?.extract()?;
            Ok(PyString::new(ctx.py, &s).into_any().unbind())
        }
        FieldType::Time => {
            if !value.is_instance_of::<PyTime>() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Not a valid time.",
                ));
            }
            let cached = get_cached_types(ctx.py)?;
            let s: String = value.call_method0(cached.str_isoformat.bind(ctx.py))?.extract()?;
            Ok(PyString::new(ctx.py, &s).into_any().unbind())
        }
        FieldType::Any => serialize_any_value(value, ctx.py, None),
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unsupported primitive type",
        )),
    }
}

pub fn dump<'py>(
    py: Python<'py>,
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    none_value_handling: Option<&str>,
    global_decimal_places: Option<i32>,
) -> PyResult<Py<PyAny>> {
    let ctx = DictContext {
        py,
        none_value_handling,
        global_decimal_places,
    };

    serialize_root_type(value, descriptor, &ctx)
}
