use std::collections::HashMap;
use std::fmt::Write;

use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDate, PyDateTime, PyDelta, PyDict, PyFloat, PyFrozenSet, PyInt, PyList, PySet, PyString, PyTime, PyTuple, PyDateAccess, PyDeltaAccess, PyTimeAccess, PyTzInfoAccess};
use serde::ser::{SerializeMap, SerializeSeq};
use serde::{Serialize, Serializer};
use serde_json::{json, Value};

use crate::cache::get_cached_types;
use crate::slots::get_slot_value_direct;
use crate::types::{FieldDescriptor, FieldType, TypeDescriptor, TypeKind};

fn serialize_python_int<S>(value: &Bound<'_, PyAny>, serializer: S) -> Result<S::Ok, S::Error>
where
    S: Serializer,
{
    if let Ok(i) = value.extract::<i64>() {
        serializer.serialize_i64(i)
    } else if let Ok(u) = value.extract::<u64>() {
        serializer.serialize_u64(u)
    } else {
        let s: String = value
            .str()
            .map_err(serde::ser::Error::custom)?
            .extract()
            .map_err(serde::ser::Error::custom)?;
        let num = serde_json::Number::from_string_unchecked(s);
        num.serialize(serializer)
    }
}

fn call_validator(py: Python, validator: &Py<PyAny>, value: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let result = validator.bind(py).call1((value,))?;
    if result.is_none() {
        return Ok(None);
    }
    Ok(Some(result.unbind()))
}

use crate::utils::pyany_to_json_value;

fn pylist_to_json_value(py: Python, list: &Py<PyAny>) -> Value {
    pyany_to_json_value(list.bind(py))
}

fn format_field_error_json(py: Python, field_name: &str, errors: &Py<PyAny>) -> String {
    let errors_json = pylist_to_json_value(py, errors);
    let mut map = serde_json::Map::new();
    map.insert(field_name.to_string(), errors_json);
    Value::Object(map).to_string()
}

fn format_field_item_error_json(py: Python, field_name: &str, errors: &HashMap<usize, Py<PyAny>>) -> String {
    let mut inner_map = serde_json::Map::new();
    for (idx, err_list) in errors {
        let json_val = pylist_to_json_value(py, err_list);
        inner_map.insert(idx.to_string(), json_val);
    }
    let mut map = serde_json::Map::new();
    map.insert(field_name.to_string(), Value::Object(inner_map));
    Value::Object(map).to_string()
}

fn format_field_dict_error_json(py: Python, field_name: &str, errors: &HashMap<String, Py<PyAny>>) -> String {
    let mut inner_map = serde_json::Map::new();
    for (key, err_list) in errors {
        let json_val = pylist_to_json_value(py, err_list);
        inner_map.insert(key.clone(), json_val);
    }
    let mut map = serde_json::Map::new();
    map.insert(field_name.to_string(), Value::Object(inner_map));
    Value::Object(map).to_string()
}

pub struct StreamingContext<'a, 'py> {
    pub py: Python<'py>,
    pub none_value_handling: Option<&'a str>,
    pub global_decimal_places: Option<i32>,
}

pub struct AnyValueSerializer<'a, 'py> {
    pub value: &'a Bound<'py, PyAny>,
    pub field_name: Option<&'a str>,
}

impl Serialize for AnyValueSerializer<'_, '_> {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if self.value.is_none() {
            return serializer.serialize_none();
        }
        if self.value.is_instance_of::<PyBool>() {
            let b: bool = self.value.extract().map_err(serde::ser::Error::custom)?;
            return serializer.serialize_bool(b);
        }
        if self.value.is_instance_of::<PyInt>() {
            return serialize_python_int(self.value, serializer);
        }
        if self.value.is_instance_of::<PyFloat>() {
            let f: f64 = self.value.extract().map_err(serde::ser::Error::custom)?;
            return serializer.serialize_f64(f);
        }
        if let Ok(py_str) = self.value.cast::<PyString>() {
            let s = py_str.to_str().map_err(serde::ser::Error::custom)?;
            return serializer.serialize_str(s);
        }
        if let Ok(list) = self.value.cast::<PyList>() {
            let mut seq = serializer.serialize_seq(Some(list.len()))?;
            for item in list.iter() {
                seq.serialize_element(&AnyValueSerializer {
                    value: &item,
                    field_name: self.field_name,
                })?;
            }
            return seq.end();
        }
        if let Ok(dict) = self.value.cast::<PyDict>() {
            let mut map = serializer.serialize_map(Some(dict.len()))?;
            for (k, v) in dict.iter() {
                let key = k.cast::<PyString>().map_err(|_| {
                    serde::ser::Error::custom(match self.field_name {
                        Some(name) => format!(
                            "{{\"{name}\": [\"Not a valid JSON-serializable value.\"]}}"
                        ),
                        None => "Any field dict keys must be strings".to_string(),
                    })
                })?.to_str().map_err(serde::ser::Error::custom)?;
                map.serialize_entry(
                    key,
                    &AnyValueSerializer {
                        value: &v,
                        field_name: self.field_name,
                    },
                )?;
            }
            return map.end();
        }
        Err(serde::ser::Error::custom(match self.field_name {
            Some(name) => format!(
                "{{\"{name}\": [\"Not a valid JSON-serializable value.\"]}}"
            ),
            None => format!(
                "Any field value must be JSON-serializable (str/int/float/bool/None/list/dict), got: {}",
                self.value.get_type().name().map_err(serde::ser::Error::custom)?
            ),
        }))
    }
}

pub struct FieldValueSerializer<'a, 'py> {
    pub value: &'a Bound<'py, PyAny>,
    pub field: &'a FieldDescriptor,
    pub ctx: &'a StreamingContext<'a, 'py>,
}

impl<'py> Serialize for FieldValueSerializer<'_, 'py> {
    #[allow(clippy::too_many_lines)]
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if self.value.is_none() {
            return serializer.serialize_none();
        }

        match self.field.field_type {
            FieldType::Str => {
                let py_str: &Bound<'_, PyString> = self.value.cast().map_err(|_| {
                    serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid string.\"]}}",
                        self.field.name
                    ))
                })?;
                let s = py_str.to_str().map_err(serde::ser::Error::custom)?;
                if self.field.strip_whitespaces {
                    serializer.serialize_str(s.trim())
                } else {
                    serializer.serialize_str(s)
                }
            }
            FieldType::Int => {
                if !self.value.is_instance_of::<PyInt>() || self.value.is_instance_of::<PyBool>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid integer.\"]}}",
                        self.field.name
                    )));
                }
                serialize_python_int(self.value, serializer)
            }
            FieldType::Float => {
                if self.value.is_instance_of::<PyBool>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid number.\"]}}",
                        self.field.name
                    )));
                }
                if self.value.is_instance_of::<PyInt>() {
                    serialize_python_int(self.value, serializer)
                } else if self.value.is_instance_of::<PyFloat>() {
                    let f: f64 = self.value.extract().map_err(serde::ser::Error::custom)?;
                    if f.is_nan() || f.is_infinite() {
                        return Err(serde::ser::Error::custom(format!(
                            "{{\"{}\": [\"Special numeric values (nan or infinity) are not permitted.\"]}}",
                            self.field.name
                        )));
                    }
                    serializer.serialize_f64(f)
                } else {
                    Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid number.\"]}}",
                        self.field.name
                    )))
                }
            }
            FieldType::Bool => {
                if !self.value.is_instance_of::<PyBool>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid boolean.\"]}}",
                        self.field.name
                    )));
                }
                let b: bool = self.value.extract().map_err(serde::ser::Error::custom)?;
                serializer.serialize_bool(b)
            }
            FieldType::Decimal => {
                let py = self.value.py();
                let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                if !self.value.is_instance(cached.decimal_cls.bind(py)).map_err(serde::ser::Error::custom)? {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid decimal.\"]}}",
                        self.field.name
                    )));
                }

                let decimal_places = self
                    .ctx
                    .global_decimal_places
                    .or(self.field.decimal_places)
                    .filter(|&p| p >= 0);

                let decimal_value = if let Some(places) = decimal_places {
                    let cached =
                        get_cached_types(self.ctx.py).map_err(serde::ser::Error::custom)?;
                    let quantizer = if let Some(q) = cached.get_quantizer(places) { q.clone_ref(self.ctx.py) } else {
                        let quantize_str = format!("1e-{places}");
                        cached.decimal_cls.bind(self.ctx.py)
                            .call1((quantize_str,))
                            .map_err(serde::ser::Error::custom)?
                            .unbind()
                    };
                    if let Some(ref rounding) = self.field.decimal_rounding {
                        let kwargs = PyDict::new(self.ctx.py);
                        kwargs
                            .set_item(cached.str_rounding.bind(self.ctx.py), rounding.bind(self.ctx.py))
                            .map_err(serde::ser::Error::custom)?;
                        self.value
                            .call_method(cached.str_quantize.bind(self.ctx.py), (quantizer.bind(self.ctx.py),), Some(&kwargs))
                            .map_err(serde::ser::Error::custom)?
                    } else {
                        self.value
                            .call_method1(cached.str_quantize.bind(self.ctx.py), (quantizer.bind(self.ctx.py),))
                            .map_err(serde::ser::Error::custom)?
                    }
                } else {
                    self.value.clone()
                };

                let s: String = decimal_value
                    .str()
                    .map_err(serde::ser::Error::custom)?
                    .extract()
                    .map_err(serde::ser::Error::custom)?;

                serializer.serialize_str(&s)
            }
            FieldType::Uuid => {
                let py = self.value.py();
                let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                if !self.value.is_instance(cached.uuid_cls.bind(py)).map_err(serde::ser::Error::custom)? {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid UUID.\"]}}",
                        self.field.name
                    )));
                }
                let uuid_int: u128 = self.value
                    .getattr(cached.str_int.bind(py))
                    .map_err(serde::ser::Error::custom)?
                    .extract()
                    .map_err(serde::ser::Error::custom)?;
                let uuid = uuid::Uuid::from_u128(uuid_int);
                let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
                let s = uuid.hyphenated().encode_lower(&mut buf);
                serializer.serialize_str(s)
            }
            FieldType::DateTime => {
                let py = self.value.py();
                let dt: &Bound<'_, PyDateTime> = self.value.cast().map_err(|_| {
                    serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid datetime.\"]}}",
                        self.field.name
                    ))
                })?;
                if let Some(ref fmt) = self.field.datetime_format {
                    let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                    let s: String = dt
                        .call_method1(cached.str_strftime.bind(py), (fmt.as_str(),))
                        .map_err(serde::ser::Error::custom)?
                        .extract()
                        .map_err(serde::ser::Error::custom)?;
                    serializer.serialize_str(&s)
                } else {
                    let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                    let mut buf = arrayvec::ArrayString::<32>::new();
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
                    if let Some(tz) = dt.get_tzinfo() {
                        if tz.is(cached.utc_tz.bind(py)) {

                            buf.push_str("+00:00");
                        } else {
                            let offset = tz.call_method1(cached.str_utcoffset.bind(py), (dt,))
                                .map_err(serde::ser::Error::custom)?;
                            if let Ok(delta) = offset.cast::<PyDelta>() {
                                let total_seconds = delta.get_days() * 86400 + delta.get_seconds();
                                if total_seconds >= 0 {
                                    write!(buf, "+{:02}:{:02}", total_seconds / 3600, (total_seconds % 3600) / 60).unwrap();
                                } else {
                                    let abs = total_seconds.abs();
                                    write!(buf, "-{:02}:{:02}", abs / 3600, (abs % 3600) / 60).unwrap();
                                }
                            }
                        }
                    }
                    serializer.serialize_str(&buf)
                }
            }
            FieldType::Date => {
                let d: &Bound<'_, PyDate> = if let Ok(dt) = self.value.cast::<PyDateTime>() {
                    // Serialize date from datetime directly
                    let mut buf = arrayvec::ArrayString::<10>::new();
                    write!(buf, "{:04}-{:02}-{:02}", dt.get_year(), dt.get_month(), dt.get_day()).unwrap();
                    return serializer.serialize_str(&buf);
                } else if let Ok(d) = self.value.cast::<PyDate>() {
                    d
                } else {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid date.\"]}}",
                        self.field.name
                    )));
                };
                let mut buf = arrayvec::ArrayString::<10>::new();
                write!(buf, "{:04}-{:02}-{:02}", d.get_year(), d.get_month(), d.get_day()).unwrap();
                serializer.serialize_str(&buf)
            }
            FieldType::Time => {
                let py = self.value.py();
                let t: &Bound<'_, PyTime> = self.value.cast().map_err(|_| {
                    serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid time.\"]}}",
                        self.field.name
                    ))
                })?;
                let mut buf = arrayvec::ArrayString::<21>::new();
                let micros = t.get_microsecond();
                if micros == 0 {
                    write!(buf, "{:02}:{:02}:{:02}",
                        t.get_hour(), t.get_minute(), t.get_second()).unwrap();
                } else {
                    write!(buf, "{:02}:{:02}:{:02}.{:06}",
                        t.get_hour(), t.get_minute(), t.get_second(), micros).unwrap();
                }
                if let Some(tz) = t.get_tzinfo() {
                    let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                    if tz.is(cached.utc_tz.bind(py)) {
                        buf.push_str("+00:00");
                    } else {
                        let offset = tz.call_method1(cached.str_utcoffset.bind(py), (py.None(),))
                            .map_err(serde::ser::Error::custom)?;
                        if let Ok(delta) = offset.cast::<PyDelta>() {
                            let total_seconds = delta.get_days() * 86400 + delta.get_seconds();
                            if total_seconds >= 0 {
                                write!(buf, "+{:02}:{:02}", total_seconds / 3600, (total_seconds % 3600) / 60).unwrap();
                            } else {
                                let abs = total_seconds.abs();
                                write!(buf, "-{:02}:{:02}", abs / 3600, (abs % 3600) / 60).unwrap();
                            }
                        }
                    }
                }
                serializer.serialize_str(&buf)
            }
            FieldType::List => {
                if !self.value.is_instance_of::<PyList>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid list.\"]}}",
                        self.field.name
                    )));
                }
                let list = self
                    .value
                    .cast::<PyList>()
                    .map_err(serde::ser::Error::custom)?;
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("List field missing item_schema")
                })?;

                if let Some(ref item_validator) = self.field.item_validator {
                    let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                    for (idx, item) in list.iter().enumerate() {
                        if let Some(errors) = call_validator(self.ctx.py, item_validator, &item).map_err(serde::ser::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    if let Some(ref errs) = item_errors {
                        return Err(serde::ser::Error::custom(format_field_item_error_json(self.ctx.py, &self.field.name, errs)));
                    }
                }

                let mut seq = serializer.serialize_seq(Some(list.len()))?;
                for item in list.iter() {
                    seq.serialize_element(&FieldValueSerializer {
                        value: &item,
                        field: item_schema,
                        ctx: self.ctx,
                    })?;
                }
                seq.end()
            }
            FieldType::Dict => {
                if !self.value.is_instance_of::<PyDict>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid mapping.\"]}}",
                        self.field.name
                    )));
                }
                let dict = self
                    .value
                    .cast::<PyDict>()
                    .map_err(serde::ser::Error::custom)?;
                let value_schema = self.field.value_schema.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Dict field missing value_schema")
                })?;

                if let Some(ref value_validator) = self.field.value_validator {
                    let mut value_errors: Option<HashMap<String, Py<PyAny>>> = None;
                    for (k, v) in dict.iter() {
                        let key = k.cast::<PyString>().map_err(serde::ser::Error::custom)?
                            .to_str().map_err(serde::ser::Error::custom)?;
                        if let Some(errors) = call_validator(self.ctx.py, value_validator, &v).map_err(serde::ser::Error::custom)? {
                            value_errors.get_or_insert_with(HashMap::new).insert(key.to_string(), errors);
                        }
                    }
                    if let Some(ref errs) = value_errors {
                        return Err(serde::ser::Error::custom(format_field_dict_error_json(self.ctx.py, &self.field.name, errs)));
                    }
                }

                let mut map = serializer.serialize_map(Some(dict.len()))?;
                for (k, v) in dict.iter() {
                    let key = k.cast::<PyString>().map_err(serde::ser::Error::custom)?
                        .to_str().map_err(serde::ser::Error::custom)?;
                    map.serialize_entry(
                        key,
                        &FieldValueSerializer {
                            value: &v,
                            field: value_schema,
                            ctx: self.ctx,
                        },
                    )?;
                }
                map.end()
            }
            FieldType::Nested => {
                let nested_schema = self.field.nested_schema.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Nested field missing nested_schema")
                })?;
                let py = self.value.py();
                if !self.value.is_instance(nested_schema.cls.bind(py)).map_err(serde::ser::Error::custom)? {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid nested object.\"]}}",
                        self.field.name
                    )));
                }
                DataclassSerializer {
                    obj: self.value,
                    fields: &nested_schema.fields,
                    ctx: self.ctx,
                }
                .serialize(serializer)
            }
            FieldType::StrEnum => {
                let py = self.value.py();
                let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                if let Some(ref enum_cls) = self.field.enum_cls {
                    if !self.value.is_instance(enum_cls.bind(py)).map_err(serde::ser::Error::custom)? {
                        let value_type_name: String = self.value.get_type().name().map_err(serde::ser::Error::custom)?.extract().map_err(serde::ser::Error::custom)?;
                        let enum_name = self.field.enum_name.as_deref().unwrap_or("Enum");
                        let members_repr = self.field.enum_members_repr.as_deref().unwrap_or("[]");
                        return Err(serde::ser::Error::custom(format!(
                            "[\"Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}\"]"
                        )));
                    }
                }
                let enum_value = self
                    .value
                    .getattr(cached.str_value.bind(py))
                    .map_err(serde::ser::Error::custom)?;
                let s = enum_value.cast::<PyString>().map_err(serde::ser::Error::custom)?
                    .to_str().map_err(serde::ser::Error::custom)?;
                serializer.serialize_str(s)
            }
            FieldType::IntEnum => {
                let py = self.value.py();
                let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                if let Some(ref enum_cls) = self.field.enum_cls {
                    if !self.value.is_instance(enum_cls.bind(py)).map_err(serde::ser::Error::custom)? {
                        let value_type_name: String = self.value.get_type().name().map_err(serde::ser::Error::custom)?.extract().map_err(serde::ser::Error::custom)?;
                        let enum_name = self.field.enum_name.as_deref().unwrap_or("Enum");
                        let members_repr = self.field.enum_members_repr.as_deref().unwrap_or("[]");
                        return Err(serde::ser::Error::custom(format!(
                            "[\"Expected {enum_name} instance, got {value_type_name}. Allowed values: {members_repr}\"]"
                        )));
                    }
                }
                let enum_value = self
                    .value
                    .getattr(cached.str_value.bind(py))
                    .map_err(serde::ser::Error::custom)?;
                let i: i64 = enum_value.extract().map_err(serde::ser::Error::custom)?;
                serializer.serialize_i64(i)
            }
            FieldType::Set => {
                if !self.value.is_instance_of::<PySet>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid set.\"]}}",
                        self.field.name
                    )));
                }
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Set field missing item_schema")
                })?;

                let items: Vec<Bound<'py, PyAny>> = self.value.try_iter()
                    .map_err(serde::ser::Error::custom)?
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(serde::ser::Error::custom)?;

                if let Some(ref item_validator) = self.field.item_validator {
                    let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                    for (idx, item) in items.iter().enumerate() {
                        if let Some(errors) = call_validator(self.ctx.py, item_validator, item).map_err(serde::ser::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    if let Some(ref errs) = item_errors {
                        return Err(serde::ser::Error::custom(format_field_item_error_json(self.ctx.py, &self.field.name, errs)));
                    }
                }

                let mut seq = serializer.serialize_seq(Some(items.len()))?;
                for item in &items {
                    seq.serialize_element(&FieldValueSerializer {
                        value: item,
                        field: item_schema,
                        ctx: self.ctx,
                    })?;
                }
                seq.end()
            }
            FieldType::FrozenSet => {
                if !self.value.is_instance_of::<PyFrozenSet>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid frozenset.\"]}}",
                        self.field.name
                    )));
                }
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("FrozenSet field missing item_schema")
                })?;

                let items: Vec<Bound<'py, PyAny>> = self.value.try_iter()
                    .map_err(serde::ser::Error::custom)?
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(serde::ser::Error::custom)?;

                if let Some(ref item_validator) = self.field.item_validator {
                    let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                    for (idx, item) in items.iter().enumerate() {
                        if let Some(errors) = call_validator(self.ctx.py, item_validator, item).map_err(serde::ser::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    if let Some(ref errs) = item_errors {
                        return Err(serde::ser::Error::custom(format_field_item_error_json(self.ctx.py, &self.field.name, errs)));
                    }
                }

                let mut seq = serializer.serialize_seq(Some(items.len()))?;
                for item in &items {
                    seq.serialize_element(&FieldValueSerializer {
                        value: item,
                        field: item_schema,
                        ctx: self.ctx,
                    })?;
                }
                seq.end()
            }
            FieldType::Tuple => {
                if !self.value.is_instance_of::<PyTuple>() {
                    return Err(serde::ser::Error::custom(format!(
                        "{{\"{}\": [\"Not a valid tuple.\"]}}",
                        self.field.name
                    )));
                }
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Tuple field missing item_schema")
                })?;

                let items: Vec<Bound<'py, PyAny>> = self.value.try_iter()
                    .map_err(serde::ser::Error::custom)?
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(serde::ser::Error::custom)?;

                if let Some(ref item_validator) = self.field.item_validator {
                    let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                    for (idx, item) in items.iter().enumerate() {
                        if let Some(errors) = call_validator(self.ctx.py, item_validator, item).map_err(serde::ser::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    if let Some(ref errs) = item_errors {
                        return Err(serde::ser::Error::custom(format_field_item_error_json(self.ctx.py, &self.field.name, errs)));
                    }
                }

                let mut seq = serializer.serialize_seq(Some(items.len()))?;
                for item in &items {
                    seq.serialize_element(&FieldValueSerializer {
                        value: item,
                        field: item_schema,
                        ctx: self.ctx,
                    })?;
                }
                seq.end()
            }
            FieldType::Union => {
                let variants = self.field.union_variants.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Union field missing union_variants")
                })?;

                for variant in variants {
                    let result = serde_json::to_value(&FieldValueSerializer {
                        value: self.value,
                        field: variant,
                        ctx: self.ctx,
                    });
                    if let Ok(json_value) = result {
                        return json_value.serialize(serializer);
                    }
                }
                Err(serde::ser::Error::custom(format!(
                    "Value does not match any union variant for field '{}'",
                    self.field.name
                )))
            }
            FieldType::Any => AnyValueSerializer {
                value: self.value,
                field_name: Some(&self.field.name),
            }
            .serialize(serializer),
        }
    }
}

pub struct DataclassSerializer<'a, 'py> {
    pub obj: &'a Bound<'py, PyAny>,
    pub fields: &'a [FieldDescriptor],
    pub ctx: &'a StreamingContext<'a, 'py>,
}

impl Serialize for DataclassSerializer<'_, '_> {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let ignore_none = self
            .ctx
            .none_value_handling
            .is_none_or(|s| s == "ignore");

        let cached = get_cached_types(self.ctx.py).map_err(serde::ser::Error::custom)?;
        let missing_sentinel = cached.missing_sentinel.bind(self.ctx.py);
        let mut map = serializer.serialize_map(None)?;

        for field in self.fields {
            let py_value = match field.slot_offset {
                Some(offset) => match unsafe { get_slot_value_direct(self.ctx.py, self.obj, offset) }
                {
                    Some(value) => value,
                    None => self
                        .obj
                        .getattr(field.name.as_str())
                        .map_err(serde::ser::Error::custom)?,
                },
                None => self
                    .obj
                    .getattr(field.name.as_str())
                    .map_err(serde::ser::Error::custom)?,
            };

            if py_value.is(missing_sentinel) || (py_value.is_none() && ignore_none) {
                continue;
            }

            if let Some(ref validator) = field.validator {
                if let Some(errors) = call_validator(self.ctx.py, validator, &py_value).map_err(serde::ser::Error::custom)? {
                    return Err(serde::ser::Error::custom(format_field_error_json(self.ctx.py, &field.name, &errors)));
                }
            }

            let key = field.serialized_name.as_ref().unwrap_or(&field.name);
            map.serialize_entry(
                key.as_str(),
                &FieldValueSerializer {
                    value: &py_value,
                    field,
                    ctx: self.ctx,
                },
            )?;
        }

        map.end()
    }
}

pub struct RootTypeSerializer<'a, 'py> {
    pub value: &'a Bound<'py, PyAny>,
    pub descriptor: &'a TypeDescriptor,
    pub ctx: &'a StreamingContext<'a, 'py>,
}

impl Serialize for RootTypeSerializer<'_, '_> {
    #[allow(clippy::too_many_lines)]
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        match self.descriptor.type_kind {
            TypeKind::Dataclass => DataclassSerializer {
                obj: self.value,
                fields: &self.descriptor.fields,
                ctx: self.ctx,
            }
            .serialize(serializer),
            TypeKind::Primitive => {
                let field_type = self.descriptor.primitive_type.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Missing primitive_type")
                })?;
                PrimitiveSerializer {
                    value: self.value,
                    field_type,
                }
                .serialize(serializer)
            }
            TypeKind::List => {
                let list = self
                    .value
                    .cast::<PyList>()
                    .map_err(serde::ser::Error::custom)?;
                let item_descriptor = self.descriptor.item_type.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Missing item_type for list")
                })?;

                let mut seq = serializer.serialize_seq(Some(list.len()))?;
                for item in list.iter() {
                    seq.serialize_element(&RootTypeSerializer {
                        value: &item,
                        descriptor: item_descriptor,
                        ctx: self.ctx,
                    })?;
                }
                seq.end()
            }
            TypeKind::Dict => {
                let dict = self
                    .value
                    .cast::<PyDict>()
                    .map_err(serde::ser::Error::custom)?;
                let value_descriptor = self.descriptor.value_type.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Missing value_type for dict")
                })?;

                let mut map = serializer.serialize_map(Some(dict.len()))?;
                for (k, v) in dict.iter() {
                    let key = k.cast::<PyString>().map_err(serde::ser::Error::custom)?
                        .to_str().map_err(serde::ser::Error::custom)?;
                    map.serialize_entry(
                        key,
                        &RootTypeSerializer {
                            value: &v,
                            descriptor: value_descriptor,
                            ctx: self.ctx,
                        },
                    )?;
                }
                map.end()
            }
            TypeKind::Optional => {
                if self.value.is_none() {
                    serializer.serialize_none()
                } else {
                    let inner_descriptor = self.descriptor.inner_type.as_ref().ok_or_else(|| {
                        serde::ser::Error::custom("Missing inner_type for optional")
                    })?;
                    RootTypeSerializer {
                        value: self.value,
                        descriptor: inner_descriptor,
                        ctx: self.ctx,
                    }
                    .serialize(serializer)
                }
            }
            TypeKind::Set | TypeKind::FrozenSet | TypeKind::Tuple => {
                let iter = self.value.try_iter().map_err(serde::ser::Error::custom)?;
                let item_descriptor = self.descriptor.item_type.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Missing item_type for collection")
                })?;
                let len_hint = self.value.len().unwrap_or(0);

                let mut seq = serializer.serialize_seq(Some(len_hint))?;
                for item_result in iter {
                    let item = item_result.map_err(serde::ser::Error::custom)?;
                    seq.serialize_element(&RootTypeSerializer {
                        value: &item,
                        descriptor: item_descriptor,
                        ctx: self.ctx,
                    })?;
                }
                seq.end()
            }
            TypeKind::Union => {
                let variants = self.descriptor.union_variants.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Missing union_variants for union")
                })?;

                for variant in variants {
                    let result = serde_json::to_value(&RootTypeSerializer {
                        value: self.value,
                        descriptor: variant,
                        ctx: self.ctx,
                    });
                    if let Ok(json_value) = result {
                        return json_value.serialize(serializer);
                    }
                }
                Err(serde::ser::Error::custom(
                    "Value does not match any union variant",
                ))
            }
        }
    }
}

pub struct PrimitiveSerializer<'a, 'py> {
    pub value: &'a Bound<'py, PyAny>,
    pub field_type: &'a FieldType,
}

impl Serialize for PrimitiveSerializer<'_, '_> {
    #[allow(clippy::too_many_lines)]
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if self.value.is_none() {
            return serializer.serialize_none();
        }

        match self.field_type {
            FieldType::Str => {
                let py_str: &Bound<'_, PyString> = self.value.cast().map_err(|_| {
                    serde::ser::Error::custom("Not a valid string.")
                })?;
                let s = py_str.to_str().map_err(serde::ser::Error::custom)?;
                serializer.serialize_str(s)
            }
            FieldType::Int => {
                if !self.value.is_instance_of::<PyInt>() || self.value.is_instance_of::<PyBool>() {
                    return Err(serde::ser::Error::custom("Not a valid integer."));
                }
                serialize_python_int(self.value, serializer)
            }
            FieldType::Float => {
                if self.value.is_instance_of::<PyBool>() {
                    return Err(serde::ser::Error::custom("Not a valid number."));
                }
                if self.value.is_instance_of::<PyInt>() {
                    serialize_python_int(self.value, serializer)
                } else if self.value.is_instance_of::<PyFloat>() {
                    let f: f64 = self.value.extract().map_err(serde::ser::Error::custom)?;
                    if f.is_nan() || f.is_infinite() {
                        return Err(serde::ser::Error::custom(
                            "Cannot serialize NaN/Infinite float",
                        ));
                    }
                    serializer.serialize_f64(f)
                } else {
                    Err(serde::ser::Error::custom("Not a valid number."))
                }
            }
            FieldType::Bool => {
                if !self.value.is_instance_of::<PyBool>() {
                    return Err(serde::ser::Error::custom("Not a valid boolean."));
                }
                let b: bool = self.value.extract().map_err(serde::ser::Error::custom)?;
                serializer.serialize_bool(b)
            }
            FieldType::Decimal => {
                let py = self.value.py();
                let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                if !self.value.is_instance(cached.decimal_cls.bind(py)).map_err(serde::ser::Error::custom)? {
                    return Err(serde::ser::Error::custom("Not a valid decimal."));
                }
                let s: String = self
                    .value
                    .str()
                    .map_err(serde::ser::Error::custom)?
                    .extract()
                    .map_err(serde::ser::Error::custom)?;
                serializer.serialize_str(&s)
            }
            FieldType::Uuid => {
                let py = self.value.py();
                let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                if !self.value.is_instance(cached.uuid_cls.bind(py)).map_err(serde::ser::Error::custom)? {
                    return Err(serde::ser::Error::custom("Not a valid UUID."));
                }
                let uuid_int: u128 = self.value
                    .getattr(cached.str_int.bind(py))
                    .map_err(serde::ser::Error::custom)?
                    .extract()
                    .map_err(serde::ser::Error::custom)?;
                let uuid = uuid::Uuid::from_u128(uuid_int);
                let mut buf = [0u8; uuid::fmt::Hyphenated::LENGTH];
                let s = uuid.hyphenated().encode_lower(&mut buf);
                serializer.serialize_str(s)
            }
            FieldType::DateTime => {
                let py = self.value.py();
                let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                let dt: &Bound<'_, PyDateTime> = self.value.cast()
                    .map_err(|_| serde::ser::Error::custom("Not a valid datetime."))?;
                let mut buf = arrayvec::ArrayString::<32>::new();
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
                if let Some(tz) = dt.get_tzinfo() {
                    if tz.is(cached.utc_tz.bind(py)) {

                        buf.push_str("+00:00");
                    } else {
                        let offset = tz.call_method1(cached.str_utcoffset.bind(py), (dt,))
                            .map_err(serde::ser::Error::custom)?;
                        if let Ok(delta) = offset.cast::<PyDelta>() {
                            let total_seconds = delta.get_days() * 86400 + delta.get_seconds();
                            if total_seconds >= 0 {
                                write!(buf, "+{:02}:{:02}", total_seconds / 3600, (total_seconds % 3600) / 60).unwrap();
                            } else {
                                let abs = total_seconds.abs();
                                write!(buf, "-{:02}:{:02}", abs / 3600, (abs % 3600) / 60).unwrap();
                            }
                        }
                    }
                }
                serializer.serialize_str(&buf)
            }
            FieldType::Date => {
                let d: &Bound<'_, PyDate> = self.value.cast()
                    .map_err(|_| serde::ser::Error::custom("Not a valid date."))?;
                let mut buf = arrayvec::ArrayString::<10>::new();
                write!(buf, "{:04}-{:02}-{:02}", d.get_year(), d.get_month(), d.get_day()).unwrap();
                serializer.serialize_str(&buf)
            }
            FieldType::Time => {
                let py = self.value.py();
                let t: &Bound<'_, PyTime> = self.value.cast()
                    .map_err(|_| serde::ser::Error::custom("Not a valid time."))?;
                let mut buf = arrayvec::ArrayString::<21>::new();
                let micros = t.get_microsecond();
                if micros == 0 {
                    write!(buf, "{:02}:{:02}:{:02}",
                        t.get_hour(), t.get_minute(), t.get_second()).unwrap();
                } else {
                    write!(buf, "{:02}:{:02}:{:02}.{:06}",
                        t.get_hour(), t.get_minute(), t.get_second(), micros).unwrap();
                }
                if let Some(tz) = t.get_tzinfo() {
                    let cached = get_cached_types(py).map_err(serde::ser::Error::custom)?;
                    if tz.is(cached.utc_tz.bind(py)) {

                        buf.push_str("+00:00");
                    } else {
                        let offset = tz.call_method1(cached.str_utcoffset.bind(py), (py.None(),))
                            .map_err(serde::ser::Error::custom)?;
                        if let Ok(delta) = offset.cast::<PyDelta>() {
                            let total_seconds = delta.get_days() * 86400 + delta.get_seconds();
                            if total_seconds >= 0 {
                                write!(buf, "+{:02}:{:02}", total_seconds / 3600, (total_seconds % 3600) / 60).unwrap();
                            } else {
                                let abs = total_seconds.abs();
                                write!(buf, "-{:02}:{:02}", abs / 3600, (abs % 3600) / 60).unwrap();
                            }
                        }
                    }
                }
                serializer.serialize_str(&buf)
            }
            FieldType::Any => AnyValueSerializer {
                value: self.value,
                field_name: None,
            }
            .serialize(serializer),
            _ => Err(serde::ser::Error::custom("Unsupported primitive type")),
        }
    }
}

pub fn dump_to_bytes<'py>(
    py: Python<'py>,
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    none_value_handling: Option<&str>,
    global_decimal_places: Option<i32>,
) -> PyResult<Vec<u8>> {
    let ctx = StreamingContext {
        py,
        none_value_handling,
        global_decimal_places,
    };

    let serializer = RootTypeSerializer {
        value,
        descriptor,
        ctx: &ctx,
    };

    serde_json::to_vec(&serializer)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}
