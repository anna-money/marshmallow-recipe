use std::collections::HashMap;
use std::fmt;
use smallbitvec::SmallBitVec;

use once_cell::sync::Lazy;
use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyDate, PyTime, PyDateTime, PyTzInfo, PyDelta, PySet, PyFrozenSet, PyTuple};
use regex::Regex;
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::cache::get_cached_types;

static SERDE_LOCATION_SUFFIX: Lazy<Regex> =
    Lazy::new(|| Regex::new(r" at line \d+ column \d+").unwrap());

/// Parse ISO date string (YYYY-MM-DD) into (year, month, day)
#[inline]
fn parse_iso_date(s: &str) -> Option<(i32, u8, u8)> {
    if s.len() != 10 || s.as_bytes()[4] != b'-' || s.as_bytes()[7] != b'-' {
        return None;
    }
    let year: i32 = s[0..4].parse().ok()?;
    let month: u8 = s[5..7].parse().ok()?;
    let day: u8 = s[8..10].parse().ok()?;
    if month < 1 || month > 12 || day < 1 || day > 31 {
        return None;
    }
    Some((year, month, day))
}

/// Parse ISO time string (HH:MM:SS or HH:MM:SS.ffffff) into (hour, minute, second, microsecond)
#[inline]
fn parse_iso_time(s: &str) -> Option<(u8, u8, u8, u32)> {
    let len = s.len();
    if len < 8 || s.as_bytes()[2] != b':' || s.as_bytes()[5] != b':' {
        return None;
    }
    let hour: u8 = s[0..2].parse().ok()?;
    let minute: u8 = s[3..5].parse().ok()?;
    let second: u8 = s[6..8].parse().ok()?;
    if hour > 23 || minute > 59 || second > 59 {
        return None;
    }
    let microsecond = if len > 8 && s.as_bytes()[8] == b'.' {
        let frac = &s[9..];
        let frac_len = frac.len().min(6);
        let frac_val: u32 = frac[..frac_len].parse().ok()?;
        // Pad to microseconds (6 digits)
        frac_val * 10u32.pow((6 - frac_len) as u32)
    } else {
        0
    };
    Some((hour, minute, second, microsecond))
}

/// Parse RFC 3339 datetime into components
/// Format: YYYY-MM-DDTHH:MM:SS[.ffffff][Z|+HH:MM|-HH:MM]
#[inline]
fn parse_rfc3339_datetime(s: &str) -> Option<(i32, u8, u8, u8, u8, u8, u32, i32)> {
    let len = s.len();
    if len < 19 {
        return None;
    }
    // Parse date part
    let (year, month, day) = parse_iso_date(&s[0..10])?;

    // Check T separator
    let sep = s.as_bytes()[10];
    if sep != b'T' && sep != b't' && sep != b' ' {
        return None;
    }

    // Find timezone part
    let tz_start = s[11..].find(|c| c == 'Z' || c == 'z' || c == '+' || c == '-')
        .map(|i| i + 11);

    let time_end = tz_start.unwrap_or(len);
    let time_str = &s[11..time_end];

    // Parse time part
    let (hour, minute, second, microsecond) = parse_iso_time(time_str)?;

    // Parse timezone offset in seconds
    let offset_seconds = match tz_start {
        None => 0, // No timezone means UTC (per JSON convention)
        Some(idx) => {
            let tz_char = s.as_bytes()[idx];
            if tz_char == b'Z' || tz_char == b'z' {
                0
            } else {
                // +HH:MM or -HH:MM
                let tz_str = &s[idx..];
                if tz_str.len() < 6 || tz_str.as_bytes()[3] != b':' {
                    return None;
                }
                let sign = if tz_char == b'+' { 1 } else { -1 };
                let tz_hour: i32 = tz_str[1..3].parse().ok()?;
                let tz_min: i32 = tz_str[4..6].parse().ok()?;
                sign * (tz_hour * 3600 + tz_min * 60)
            }
        }
    };

    Some((year, month, day, hour, minute, second, microsecond, offset_seconds))
}

/// Create a PyDateTime from parsed components with timezone
#[inline]
fn create_pydatetime_with_offset(
    py: Python,
    year: i32,
    month: u8,
    day: u8,
    hour: u8,
    minute: u8,
    second: u8,
    microsecond: u32,
    offset_seconds: i32,
) -> PyResult<Py<PyAny>> {
    if offset_seconds == 0 {
        let tz = PyTzInfo::utc(py)?;
        PyDateTime::new(py, year, month, day, hour, minute, second, microsecond, Some(&tz.as_borrowed()))
            .map(|dt| dt.into_any().unbind())
    } else {
        let delta = PyDelta::new(py, 0, offset_seconds, 0, true)?;
        let tz = PyTzInfo::fixed_offset(py, &delta)?;
        PyDateTime::new(py, year, month, day, hour, minute, second, microsecond, Some(&tz))
            .map(|dt| dt.into_any().unbind())
    }
}

fn strip_serde_locations(s: &str) -> String {
    SERDE_LOCATION_SUFFIX.replace_all(s, "").into_owned()
}

// serde_json's private token for arbitrary precision numbers
const SERDE_JSON_NUMBER_TOKEN: &str = "$serde_json::private::Number";
use crate::deserialize::{LoadContext, deserialize_field_value, deserialize_root_type};
use crate::slots::set_slot_value_direct;
use crate::types::{FieldDescriptor, FieldType, TypeDescriptor, TypeKind};

/// Check if a JSON number string represents a float (has decimal point or exponent).
/// JSON floats: 3.14, 1e10, 1.5E-3
/// JSON integers: 123, -456, 9223372036854775808
fn is_json_float_string(s: &str) -> bool {
    s.contains('.') || s.contains('e') || s.contains('E')
}

fn err_json(field_name: &str, message: &str) -> String {
    if field_name.is_empty() {
        json!([message]).to_string()
    } else {
        let mut map = serde_json::Map::new();
        map.insert(field_name.to_string(), json!([message]));
        Value::Object(map).to_string()
    }
}

use crate::utils::pyany_to_json_value;

fn pylist_to_json_value(py: Python, list: &Py<PyAny>) -> PyResult<Value> {
    pyany_to_json_value(list.bind(py))
}

fn err_json_from_list(py: Python, field_name: &str, errors: &Py<PyAny>) -> String {
    let errors_json = pylist_to_json_value(py, errors).unwrap_or_else(|_| json!(["Validation error"]));

    if field_name.is_empty() {
        errors_json.to_string()
    } else {
        let mut map = serde_json::Map::new();
        map.insert(field_name.to_string(), errors_json);
        Value::Object(map).to_string()
    }
}

/// Returns the error message for a field type when wrong JSON type is received.
/// This ensures error messages describe the expected type, not the received JSON type.
fn get_type_error_message(field_type: &FieldType) -> &'static str {
    match field_type {
        FieldType::Str => "Not a valid string.",
        FieldType::Int => "Not a valid integer.",
        FieldType::Float => "Not a valid number.",
        FieldType::Bool => "Not a valid boolean.",
        FieldType::Decimal => "Not a valid number.",
        FieldType::DateTime => "Not a valid datetime.",
        FieldType::Date => "Not a valid date.",
        FieldType::Time => "Not a valid time.",
        FieldType::Uuid => "Not a valid UUID.",
        FieldType::List => "Not a valid list.",
        FieldType::Set => "Not a valid set.",
        FieldType::FrozenSet => "Not a valid frozenset.",
        FieldType::Tuple => "Not a valid tuple.",
        FieldType::Dict => "Not a valid dict.",
        FieldType::Nested => "Not a valid object.",
        FieldType::StrEnum | FieldType::IntEnum => "Invalid enum value.",
        FieldType::Any | FieldType::Union => "Invalid value.",
    }
}

fn format_item_errors(py: Python, errors: &HashMap<usize, Py<PyAny>>) -> String {
    let mut map = serde_json::Map::new();
    for (idx, err_list) in errors.iter() {
        let json_val = pylist_to_json_value(py, err_list).unwrap_or_else(|_| json!(["Validation error"]));
        map.insert(idx.to_string(), json_val);
    }
    Value::Object(map).to_string()
}

fn call_validator(py: Python, validator: &Py<PyAny>, value: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let result = validator.bind(py).call1((value,))?;
    if result.is_none() {
        return Ok(None);
    }
    Ok(Some(result.unbind()))
}

fn try_wrap_err_json(field_name: &str, inner: &str) -> Option<String> {
    let cleaned = strip_serde_locations(inner);
    let inner_value: Value = serde_json::from_str(&cleaned).ok()?;

    if field_name.is_empty() {
        return Some(inner_value.to_string());
    }

    let mut map = serde_json::Map::new();
    map.insert(field_name.to_string(), inner_value);
    Some(Value::Object(map).to_string())
}

fn wrap_err_json(field_name: &str, inner: &str) -> String {
    try_wrap_err_json(field_name, inner).unwrap_or_else(|| inner.to_string())
}

fn json_value_to_py(py: Python, value: &serde_json::Value) -> PyResult<Py<PyAny>> {
    use pyo3::types::PyBool;
    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => {
            let py_bool = (*b).into_pyobject(py)?;
            Ok(<pyo3::Bound<'_, PyBool> as Clone>::clone(&py_bool).into_any().unbind())
        }
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                return Ok(i.into_pyobject(py)?.into_any().unbind());
            }
            if let Some(u) = n.as_u64() {
                return Ok(u.into_pyobject(py)?.into_any().unbind());
            }
            let s = n.to_string();
            if is_json_float_string(&s) {
                let f: f64 = s.parse().map_err(|_| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid number")
                })?;
                Ok(f.into_pyobject(py)?.into_any().unbind())
            } else {
                let cached = get_cached_types(py)?;
                cached.int_cls.bind(py).call1((&s,)).map(|i| i.unbind())
            }
        }
        serde_json::Value::String(s) => Ok(s.clone().into_pyobject(py)?.into_any().unbind()),
        serde_json::Value::Array(arr) => {
            let list = PyList::empty(py);
            for item in arr {
                list.append(json_value_to_py(py, item)?)?;
            }
            Ok(list.into_any().unbind())
        }
        serde_json::Value::Object(obj) => {
            let dict = PyDict::new(py);
            for (k, v) in obj {
                dict.set_item(k, json_value_to_py(py, v)?)?;
            }
            Ok(dict.into_any().unbind())
        }
    }
}

fn json_error_to_py(py: Python, value: &serde_json::Value) -> PyResult<Py<PyAny>> {
    match value {
        serde_json::Value::Object(obj) => {
            let dict = PyDict::new(py);
            for (k, v) in obj {
                let key: Py<PyAny> = if k.chars().all(|c| c.is_ascii_digit()) && !k.is_empty() {
                    match k.parse::<i64>() {
                        Ok(n) => n.into_pyobject(py)?.into_any().unbind(),
                        Err(_) => {
                            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                                "Index {} is too large",
                                k
                            )));
                        }
                    }
                } else {
                    k.clone().into_pyobject(py)?.into_any().unbind()
                };
                dict.set_item(key, json_error_to_py(py, v)?)?;
            }
            Ok(dict.into_any().unbind())
        }
        serde_json::Value::Array(arr) => {
            let list = PyList::empty(py);
            for item in arr {
                list.append(json_error_to_py(py, item)?)?;
            }
            Ok(list.into_any().unbind())
        }
        serde_json::Value::String(s) => Ok(s.clone().into_pyobject(py)?.into_any().unbind()),
        _ => json_value_to_py(py, value),
    }
}

pub struct StreamingContext<'a, 'py> {
    pub py: Python<'py>,
    pub post_loads: Option<&'a Bound<'py, PyDict>>,
}

pub struct TypeDescriptorSeed<'a, 'py> {
    pub ctx: &'a StreamingContext<'a, 'py>,
    pub descriptor: &'a TypeDescriptor,
}

impl<'a, 'py, 'de> DeserializeSeed<'de> for TypeDescriptorSeed<'a, 'py> {
    type Value = Py<PyAny>;

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: de::Deserializer<'de>,
    {
        match self.descriptor.type_kind {
            TypeKind::Dataclass => {
                let cls = self.descriptor.cls.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing cls for dataclass")
                })?;
                if self.descriptor.can_use_direct_slots {
                    deserializer.deserialize_map(DataclassDirectSlotsVisitor {
                        ctx: self.ctx,
                        cls: cls.bind(self.ctx.py),
                        fields: &self.descriptor.fields,
                        field_lookup: &self.descriptor.field_lookup,
                    })
                } else {
                    deserializer.deserialize_map(DataclassVisitor {
                        ctx: self.ctx,
                        cls: cls.bind(self.ctx.py),
                        fields: &self.descriptor.fields,
                        field_lookup: &self.descriptor.field_lookup,
                    })
                }
            }
            TypeKind::Primitive => {
                let field_type = self.descriptor.primitive_type.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing primitive_type")
                })?;
                deserialize_primitive_streaming(self.ctx.py, deserializer, field_type)
            }
            TypeKind::List => {
                let item_descriptor = self.descriptor.item_type.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing item_type for list")
                })?;
                deserializer.deserialize_seq(ListVisitor {
                    ctx: self.ctx,
                    item_descriptor,
                })
            }
            TypeKind::Dict => {
                let value_descriptor = self.descriptor.value_type.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing value_type for dict")
                })?;
                deserializer.deserialize_map(DictVisitor {
                    ctx: self.ctx,
                    value_descriptor,
                })
            }
            TypeKind::Optional => {
                deserializer.deserialize_option(OptionalVisitor {
                    ctx: self.ctx,
                    inner_descriptor: self.descriptor.inner_type.as_deref(),
                })
            }
            TypeKind::Set => {
                let item_descriptor = self.descriptor.item_type.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing item_type for set")
                })?;
                deserializer.deserialize_seq(SetVisitor {
                    ctx: self.ctx,
                    item_descriptor,
                })
            }
            TypeKind::FrozenSet => {
                let item_descriptor = self.descriptor.item_type.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing item_type for frozenset")
                })?;
                deserializer.deserialize_seq(FrozenSetVisitor {
                    ctx: self.ctx,
                    item_descriptor,
                })
            }
            TypeKind::Tuple => {
                let item_descriptor = self.descriptor.item_type.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing item_type for tuple")
                })?;
                deserializer.deserialize_seq(TupleVisitor {
                    ctx: self.ctx,
                    item_descriptor,
                })
            }
            TypeKind::Union => {
                let variants = self.descriptor.union_variants.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing union_variants for union")
                })?;
                let value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
                let py_value = json_value_to_py(self.ctx.py, &value).map_err(de::Error::custom)?;
                let dict_ctx = LoadContext {
                    py: self.ctx.py,
                    post_loads: self.ctx.post_loads,
                };
                for variant in variants.iter() {
                    if let Ok(result) = deserialize_root_type(&py_value.bind(self.ctx.py), variant, &dict_ctx) {
                        return Ok(result);
                    }
                }
                Err(de::Error::custom("Value does not match any union variant"))
            }
        }
    }
}

pub struct FieldDescriptorSeed<'a, 'py> {
    pub ctx: &'a StreamingContext<'a, 'py>,
    pub field: &'a FieldDescriptor,
}

impl<'a, 'py, 'de> DeserializeSeed<'de> for FieldDescriptorSeed<'a, 'py> {
    type Value = Py<PyAny>;

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: de::Deserializer<'de>,
    {
        if self.field.field_type == FieldType::Any {
            let json_value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
            return json_value_to_py(self.ctx.py, &json_value).map_err(de::Error::custom);
        }
        if self.field.field_type == FieldType::Union {
            let variants = self.field.union_variants.as_ref().ok_or_else(|| {
                de::Error::custom("Union field missing union_variants")
            })?;
            let value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
            let py_value = json_value_to_py(self.ctx.py, &value).map_err(de::Error::custom)?;
            let dict_ctx = LoadContext {
                py: self.ctx.py,
                post_loads: self.ctx.post_loads,
            };
            for variant in variants.iter() {
                if let Ok(result) = deserialize_field_value(&py_value.bind(self.ctx.py), variant, &dict_ctx) {
                    return Ok(result);
                }
            }
            return Err(de::Error::custom(format!(
                "Value does not match any union variant for field '{}'",
                self.field.name
            )));
        }
        deserializer.deserialize_any(FieldValueVisitor {
            ctx: self.ctx,
            field: self.field,
        })
    }
}

struct FieldValueVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    field: &'a FieldDescriptor,
}

impl<'a, 'py, 'de> Visitor<'de> for FieldValueVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        write!(formatter, "a value for field '{}'", self.field.name)
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if !self.field.optional {
            let msg = self.field.none_error.as_deref().unwrap_or("Field may not be null.");
            return Err(de::Error::custom(err_json(&self.field.name, msg)));
        }
        Ok(self.ctx.py.None())
    }

    fn visit_none<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.visit_unit()
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: de::Deserializer<'de>,
    {
        deserializer.deserialize_any(self)
    }

    fn visit_bool<E>(self, v: bool) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        let py = self.ctx.py;
        match self.field.field_type {
            FieldType::Bool => Ok(v.into_py_any(py).map_err(de::Error::custom)?),
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error_message(&self.field.field_type));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_i64<E>(self, v: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        let py = self.ctx.py;
        match self.field.field_type {
            FieldType::Int => Ok(v.into_py_any(py).map_err(de::Error::custom)?),
            FieldType::Float => Ok((v as f64).into_py_any(py).map_err(de::Error::custom)?),
            FieldType::Decimal => {
                let cached = get_cached_types(py).map_err(de::Error::custom)?;
                let result = cached.decimal_cls.bind(py).call1((v,)).map_err(de::Error::custom)?;
                self.apply_decimal_quantize(result.unbind()).map_err(de::Error::custom)
            }
            FieldType::IntEnum => {
                let values = self.field.int_enum_values.as_ref().ok_or_else(|| {
                    de::Error::custom("IntEnum field missing int_enum_values")
                })?;
                for (key, member) in values {
                    if *key == v {
                        return Ok(member.clone_ref(py));
                    }
                }
                let msg = self.field.invalid_error.as_deref()
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let allowed: Vec<_> = values.iter().map(|(k, _)| k.to_string()).collect();
                        format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
                    });
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            FieldType::StrEnum => {
                // Integer received for StrEnum - show enum error with allowed values
                let values = self.field.str_enum_values.as_ref().ok_or_else(|| {
                    de::Error::custom("StrEnum field missing str_enum_values")
                })?;
                let msg = self.field.invalid_error.as_deref()
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let allowed: Vec<_> = values.iter().map(|(k, _)| format!("'{}'", k)).collect();
                        format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
                    });
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error_message(&self.field.field_type));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_u64<E>(self, v: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        let py = self.ctx.py;
        match self.field.field_type {
            FieldType::Int => Ok(v.into_py_any(py).map_err(de::Error::custom)?),
            FieldType::Float => Ok((v as f64).into_py_any(py).map_err(de::Error::custom)?),
            FieldType::Decimal => {
                let cached = get_cached_types(py).map_err(de::Error::custom)?;
                let result = cached.decimal_cls.bind(py).call1((v,)).map_err(de::Error::custom)?;
                self.apply_decimal_quantize(result.unbind()).map_err(de::Error::custom)
            }
            FieldType::IntEnum => {
                let values = self.field.int_enum_values.as_ref().ok_or_else(|| {
                    de::Error::custom("IntEnum field missing int_enum_values")
                })?;
                if v > i64::MAX as u64 {
                    let msg = self.field.invalid_error.as_deref()
                        .map(|s| s.to_string())
                        .unwrap_or_else(|| {
                            let allowed: Vec<_> = values.iter().map(|(k, _)| k.to_string()).collect();
                            format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
                        });
                    return Err(de::Error::custom(err_json(&self.field.name, &msg)));
                }
                let v_i64 = v as i64;
                for (key, member) in values {
                    if *key == v_i64 {
                        return Ok(member.clone_ref(py));
                    }
                }
                let msg = self.field.invalid_error.as_deref()
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let allowed: Vec<_> = values.iter().map(|(k, _)| k.to_string()).collect();
                        format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
                    });
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            FieldType::StrEnum => {
                // Integer received for StrEnum - show enum error with allowed values
                let values = self.field.str_enum_values.as_ref().ok_or_else(|| {
                    de::Error::custom("StrEnum field missing str_enum_values")
                })?;
                let msg = self.field.invalid_error.as_deref()
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let allowed: Vec<_> = values.iter().map(|(k, _)| format!("'{}'", k)).collect();
                        format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
                    });
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error_message(&self.field.field_type));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_f64<E>(self, v: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        let py = self.ctx.py;
        match self.field.field_type {
            FieldType::Float => Ok(v.into_py_any(py).map_err(de::Error::custom)?),
            FieldType::Decimal => {
                let cached = get_cached_types(py).map_err(de::Error::custom)?;
                let result = cached.decimal_cls.bind(py).call1((v.to_string(),)).map_err(de::Error::custom)?;
                self.apply_decimal_quantize(result.unbind()).map_err(de::Error::custom)
            }
            FieldType::Int => {
                let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid integer.");
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error_message(&self.field.field_type));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_str<E>(self, v: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        let py = self.ctx.py;
        match self.field.field_type {
            FieldType::Str => {
                let s = if self.field.strip_whitespaces {
                    v.trim()
                } else {
                    v
                };
                Ok(s.into_py_any(py).map_err(de::Error::custom)?)
            }
            FieldType::Decimal => {
                let cached = get_cached_types(py).map_err(de::Error::custom)?;
                match cached.decimal_cls.bind(py).call1((v,)) {
                    Ok(result) => self.apply_decimal_quantize(result.unbind()).map_err(de::Error::custom),
                    Err(_) => {
                        let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                    }
                }
            }
            FieldType::Uuid => {
                let cached = get_cached_types(py).map_err(de::Error::custom)?;
                match Uuid::parse_str(v) {
                    Ok(uuid) => cached.create_uuid_fast(py, uuid.as_u128()).map_err(de::Error::custom),
                    Err(_) => {
                        let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid UUID.");
                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                    }
                }
            }
            FieldType::DateTime => {
                if let Some(ref fmt) = self.field.datetime_format {
                    // Custom format - use Python's strptime
                    let cached = get_cached_types(py).map_err(de::Error::custom)?;
                    let datetime_cls = cached.datetime_cls.bind(py);
                    match datetime_cls.call_method1(cached.str_strptime.bind(py), (v, fmt.as_str())) {
                        Ok(dt) => {
                            let tzinfo = dt.getattr(cached.str_tzinfo.bind(py)).map_err(de::Error::custom)?;
                            if tzinfo.is_none() {
                                let kwargs = PyDict::new(py);
                                kwargs.set_item(cached.str_tzinfo.bind(py), cached.utc_tz.bind(py)).map_err(de::Error::custom)?;
                                Ok(dt.call_method(cached.str_replace.bind(py), (), Some(&kwargs)).map_err(de::Error::custom)?.unbind())
                            } else {
                                Ok(dt.unbind())
                            }
                        }
                        Err(_) => {
                            let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid datetime.");
                            Err(de::Error::custom(err_json(&self.field.name, msg)))
                        }
                    }
                } else {
                    // RFC 3339 only (e.g. "2024-12-26T10:30:45+00:00" or "...Z")
                    match parse_rfc3339_datetime(v) {
                        Some((year, month, day, hour, minute, second, microsecond, offset_seconds)) => {
                            create_pydatetime_with_offset(py, year, month, day, hour, minute, second, microsecond, offset_seconds)
                                .map_err(de::Error::custom)
                        }
                        None => {
                            let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid datetime.");
                            Err(de::Error::custom(err_json(&self.field.name, msg)))
                        }
                    }
                }
            }
            FieldType::Date => {
                match parse_iso_date(v) {
                    Some((year, month, day)) => {
                        PyDate::new(py, year, month, day)
                            .map(|d| d.into_any().unbind())
                            .map_err(de::Error::custom)
                    }
                    None => {
                        let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid date.");
                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                    }
                }
            }
            FieldType::Time => {
                match parse_iso_time(v) {
                    Some((hour, minute, second, microsecond)) => {
                        PyTime::new(py, hour, minute, second, microsecond, None)
                            .map(|t| t.into_any().unbind())
                            .map_err(de::Error::custom)
                    }
                    None => {
                        let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid time.");
                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                    }
                }
            }
            FieldType::Float => {
                match v.parse::<f64>() {
                    Ok(f) => {
                        if f.is_nan() || f.is_infinite() {
                            Err(de::Error::custom(err_json(&self.field.name, "Special numeric values (nan or infinity) are not permitted.")))
                        } else {
                            Ok(f.into_py_any(py).map_err(de::Error::custom)?)
                        }
                    }
                    Err(_) => {
                        let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                    }
                }
            }
            FieldType::StrEnum => {
                let values = self.field.str_enum_values.as_ref().ok_or_else(|| {
                    de::Error::custom("StrEnum field missing str_enum_values")
                })?;
                for (key, member) in values {
                    if key == v {
                        return Ok(member.clone_ref(py));
                    }
                }
                let msg = self.field.invalid_error.as_deref()
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let allowed: Vec<_> = values.iter().map(|(k, _)| format!("'{}'", k)).collect();
                        format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
                    });
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            FieldType::IntEnum => {
                let values = self.field.int_enum_values.as_ref().ok_or_else(|| {
                    de::Error::custom("IntEnum field missing int_enum_values")
                })?;
                let msg = self.field.invalid_error.as_deref()
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let allowed: Vec<_> = values.iter().map(|(k, _)| k.to_string()).collect();
                        format!("Not a valid choice: '{}'. Allowed values: [{}]", v, allowed.join(", "))
                    });
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error_message(&self.field.field_type));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_string<E>(self, v: String) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.visit_str(&v)
    }

    fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let py = self.ctx.py;
        match self.field.field_type {
            FieldType::List => {
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    de::Error::custom("List field missing item_schema")
                })?;
                let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
                let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                let mut idx = 0usize;
                while let Some(item) = seq.next_element_seed(FieldDescriptorSeed {
                    ctx: self.ctx,
                    field: item_schema,
                }).map_err(|e| {
                    let inner = e.to_string();
                    try_wrap_err_json(&idx.to_string(), &inner)
                        .and_then(|wrapped| try_wrap_err_json(&self.field.name, &wrapped))
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })? {
                    if let Some(ref item_validator) = self.field.item_validator {
                        if let Some(errors) = call_validator(py, item_validator, &item.bind(py)).map_err(de::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    items.push(item);
                    idx += 1;
                }
                if let Some(ref errs) = item_errors {
                    return Err(de::Error::custom(wrap_err_json(&self.field.name, &format_item_errors(py, errs))));
                }
                Ok(PyList::new(py, items).map_err(de::Error::custom)?.unbind().into())
            }
            FieldType::Set => {
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    de::Error::custom("Set field missing item_schema")
                })?;
                let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
                let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                let mut idx = 0usize;
                while let Some(item) = seq.next_element_seed(FieldDescriptorSeed {
                    ctx: self.ctx,
                    field: item_schema,
                }).map_err(|e| {
                    let inner = e.to_string();
                    try_wrap_err_json(&idx.to_string(), &inner)
                        .and_then(|wrapped| try_wrap_err_json(&self.field.name, &wrapped))
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })? {
                    if let Some(ref item_validator) = self.field.item_validator {
                        if let Some(errors) = call_validator(py, item_validator, &item.bind(py)).map_err(de::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    items.push(item);
                    idx += 1;
                }
                if let Some(ref errs) = item_errors {
                    return Err(de::Error::custom(wrap_err_json(&self.field.name, &format_item_errors(py, errs))));
                }
                Ok(PySet::new(py, &items).map_err(de::Error::custom)?.unbind().into())
            }
            FieldType::FrozenSet => {
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    de::Error::custom("FrozenSet field missing item_schema")
                })?;
                let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
                let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                let mut idx = 0usize;
                while let Some(item) = seq.next_element_seed(FieldDescriptorSeed {
                    ctx: self.ctx,
                    field: item_schema,
                }).map_err(|e| {
                    let inner = e.to_string();
                    try_wrap_err_json(&idx.to_string(), &inner)
                        .and_then(|wrapped| try_wrap_err_json(&self.field.name, &wrapped))
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })? {
                    if let Some(ref item_validator) = self.field.item_validator {
                        if let Some(errors) = call_validator(py, item_validator, &item.bind(py)).map_err(de::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    items.push(item);
                    idx += 1;
                }
                if let Some(ref errs) = item_errors {
                    return Err(de::Error::custom(wrap_err_json(&self.field.name, &format_item_errors(py, errs))));
                }
                Ok(PyFrozenSet::new(py, &items).map_err(de::Error::custom)?.unbind().into())
            }
            FieldType::Tuple => {
                let item_schema = self.field.item_schema.as_ref().ok_or_else(|| {
                    de::Error::custom("Tuple field missing item_schema")
                })?;
                let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
                let mut item_errors: Option<HashMap<usize, Py<PyAny>>> = None;
                let mut idx = 0usize;
                while let Some(item) = seq.next_element_seed(FieldDescriptorSeed {
                    ctx: self.ctx,
                    field: item_schema,
                }).map_err(|e| {
                    let inner = e.to_string();
                    try_wrap_err_json(&idx.to_string(), &inner)
                        .and_then(|wrapped| try_wrap_err_json(&self.field.name, &wrapped))
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })? {
                    if let Some(ref item_validator) = self.field.item_validator {
                        if let Some(errors) = call_validator(py, item_validator, &item.bind(py)).map_err(de::Error::custom)? {
                            item_errors.get_or_insert_with(HashMap::new).insert(idx, errors);
                        }
                    }
                    items.push(item);
                    idx += 1;
                }
                if let Some(ref errs) = item_errors {
                    return Err(de::Error::custom(wrap_err_json(&self.field.name, &format_item_errors(py, errs))));
                }
                Ok(PyTuple::new(py, &items).map_err(de::Error::custom)?.unbind().into())
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error_message(&self.field.field_type));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let py = self.ctx.py;

        // Check for serde_json arbitrary precision number
        // When arbitrary_precision is enabled, large numbers come as {"$serde_json::private::Number": "..."}
        if let FieldType::Int | FieldType::Float | FieldType::Decimal = self.field.field_type {
            // Try to peek at the first key - this is a bit hacky but necessary
            // We need to consume the map to check the key
            if let Some(key) = map.next_key::<&str>()? {
                if key == SERDE_JSON_NUMBER_TOKEN {
                    let num_str: String = map.next_value()?;
                    let is_float = is_json_float_string(&num_str);

                    return match self.field.field_type {
                        FieldType::Int => {
                            if is_float {
                                let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid integer.");
                                Err(de::Error::custom(err_json(&self.field.name, msg)))
                            } else {
                                let cached = get_cached_types(py).map_err(de::Error::custom)?;
                                match cached.int_cls.bind(py).call1((&num_str,)) {
                                    Ok(i) => Ok(i.unbind()),
                                    Err(_) => {
                                        let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid integer.");
                                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                                    }
                                }
                            }
                        }
                        FieldType::Float => {
                            match num_str.parse::<f64>() {
                                Ok(f) => Ok(f.into_py_any(py).map_err(de::Error::custom)?),
                                Err(_) => {
                                    let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                                    Err(de::Error::custom(err_json(&self.field.name, msg)))
                                }
                            }
                        }
                        FieldType::Decimal => {
                            let cached = get_cached_types(py).map_err(de::Error::custom)?;
                            match cached.decimal_cls.bind(py).call1((&num_str,)) {
                                Ok(result) => self.apply_decimal_quantize(result.unbind()).map_err(de::Error::custom),
                                Err(_) => {
                                    let msg = self.field.invalid_error.as_deref().unwrap_or("Not a valid number.");
                                    Err(de::Error::custom(err_json(&self.field.name, msg)))
                                }
                            }
                        }
                        _ => unreachable!(),
                    };
                }
                // Not a number token - it's a regular map/object being passed to a numeric field
                let default_msg = match self.field.field_type {
                    FieldType::Int => "Not a valid integer.",
                    _ => "Not a valid number.",
                };
                let msg = self.field.invalid_error.as_deref().unwrap_or(default_msg);
                return Err(de::Error::custom(err_json(&self.field.name, msg)));
            }
        }

        match self.field.field_type {
            FieldType::Dict => {
                let value_schema = self.field.value_schema.as_ref().ok_or_else(|| {
                    de::Error::custom("Dict field missing value_schema")
                })?;
                deserialize_dict_map(self.ctx, map, value_schema, &self.field.name)
            }
            FieldType::Nested => {
                let nested_schema = self.field.nested_schema.as_ref().ok_or_else(|| {
                    de::Error::custom("Nested field missing nested_schema")
                })?;
                let cls = nested_schema.cls.bind(py);
                let result = if nested_schema.can_use_direct_slots {
                    DataclassDirectSlotsVisitor {
                        ctx: self.ctx,
                        cls,
                        fields: &nested_schema.fields,
                        field_lookup: &nested_schema.field_lookup,
                    }.visit_map(map)
                } else {
                    DataclassVisitor {
                        ctx: self.ctx,
                        cls,
                        fields: &nested_schema.fields,
                        field_lookup: &nested_schema.field_lookup,
                    }.visit_map(map)
                };
                result.map_err(|e| {
                    let inner = e.to_string();
                    try_wrap_err_json(&self.field.name, &inner)
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error_message(&self.field.field_type));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }
}

impl<'a, 'py> FieldValueVisitor<'a, 'py> {
    fn apply_decimal_quantize(&self, value: Py<PyAny>) -> PyResult<Py<PyAny>> {
        let py = self.ctx.py;
        if let Some(places) = self.field.decimal_places.filter(|&p| p >= 0) {
            let cached = get_cached_types(py)?;
            let quantize_val = match cached.get_quantizer(places) {
                Some(q) => q.clone_ref(py),
                None => {
                    let quantize_str = format!("1e-{}", places);
                    cached.decimal_cls.bind(py).call1((quantize_str,))?.unbind()
                }
            };
            let quantized = if let Some(ref rounding) = self.field.decimal_rounding {
                let kwargs = PyDict::new(py);
                kwargs.set_item(cached.str_rounding.bind(py), rounding.bind(py))?;
                value.bind(py).call_method(cached.str_quantize.bind(py), (quantize_val.bind(py),), Some(&kwargs))?
            } else {
                value.bind(py).call_method1(cached.str_quantize.bind(py), (quantize_val.bind(py),))?
            };
            return Ok(quantized.unbind());
        }
        Ok(value)
    }
}

struct DataclassVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    cls: &'a Bound<'py, PyAny>,
    fields: &'a [FieldDescriptor],
    field_lookup: &'a HashMap<String, usize>,
}

impl<'a, 'py, 'de> Visitor<'de> for DataclassVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a JSON object")
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let py = self.ctx.py;
        let kwargs = PyDict::new(py);
        let mut seen_fields = SmallBitVec::from_elem(self.fields.len(), false);

        while let Some(key) = map.next_key::<&str>()? {
            if let Some(&idx) = self.field_lookup.get(key) {
                let field = &self.fields[idx];
                seen_fields.set(idx, true);
                let mut value = map.next_value_seed(FieldDescriptorSeed {
                    ctx: self.ctx,
                    field,
                })?;

                if let Some(pl) = self.ctx.post_loads {
                    if let Ok(Some(post_load_fn)) = pl.get_item(&field.name) {
                        if !post_load_fn.is_none() {
                            value = post_load_fn.call1((value,))
                                .map_err(de::Error::custom)?
                                .unbind();
                        }
                    }
                }

                if let Some(ref validator) = field.validator {
                    if let Some(errors) = call_validator(py, validator, &value.bind(py)).map_err(de::Error::custom)? {
                        return Err(de::Error::custom(err_json_from_list(py, &field.name, &errors)));
                    }
                }

                kwargs.set_item(field.name_interned.bind(py), value)
                    .map_err(de::Error::custom)?;
            } else {
                let _ = map.next_value::<serde::de::IgnoredAny>()?;
            }
        }

        for (idx, field) in self.fields.iter().enumerate() {
            if !seen_fields[idx] && !field.optional {
                let msg = field.required_error.as_deref().unwrap_or("Missing data for required field.");
                return Err(de::Error::custom(err_json(&field.name, msg)));
            }
        }

        match self.cls.call((), Some(&kwargs)) {
            Ok(o) => Ok(o.unbind()),
            Err(e) => Err(de::Error::custom(e)),
        }
    }
}

struct DataclassDirectSlotsVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    cls: &'a Bound<'py, PyAny>,
    fields: &'a [FieldDescriptor],
    field_lookup: &'a HashMap<String, usize>,
}

impl<'a, 'py, 'de> Visitor<'de> for DataclassDirectSlotsVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a JSON object")
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let py = self.ctx.py;
        let cached_types = get_cached_types(py).map_err(de::Error::custom)?;
        let object_type = cached_types.object_cls.bind(py);
        let instance = object_type.call_method1(cached_types.str_new.bind(py), (self.cls,))
            .map_err(de::Error::custom)?;

        let mut field_values: Vec<Option<Py<PyAny>>> = (0..self.fields.len()).map(|_| None).collect();

        while let Some(key) = map.next_key::<&str>()? {
            if let Some(&idx) = self.field_lookup.get(key) {
                let field = &self.fields[idx];
                let mut value = map.next_value_seed(FieldDescriptorSeed {
                    ctx: self.ctx,
                    field,
                })?;

                if let Some(pl) = self.ctx.post_loads {
                    if let Ok(Some(post_load_fn)) = pl.get_item(&field.name) {
                        if !post_load_fn.is_none() {
                            value = post_load_fn.call1((value,))
                                .map_err(de::Error::custom)?
                                .unbind();
                        }
                    }
                }

                if let Some(ref validator) = field.validator {
                    if let Some(errors) = call_validator(py, validator, &value.bind(py)).map_err(de::Error::custom)? {
                        return Err(de::Error::custom(err_json_from_list(py, &field.name, &errors)));
                    }
                }

                field_values[idx] = Some(value);
            } else {
                let _ = map.next_value::<serde::de::IgnoredAny>()?;
            }
        }

        for (idx, field) in self.fields.iter().enumerate() {
            let py_value = if let Some(value) = field_values[idx].take() {
                value
            } else if let Some(ref default_factory) = field.default_factory {
                default_factory.call0(py).map_err(de::Error::custom)?
            } else if let Some(ref default_value) = field.default_value {
                default_value.clone_ref(py)
            } else if field.optional {
                py.None()
            } else {
                let msg = field.required_error.as_deref().unwrap_or("Missing data for required field.");
                return Err(de::Error::custom(err_json(&field.name, msg)));
            };

            if let Some(offset) = field.slot_offset {
                unsafe {
                    set_slot_value_direct(&instance, offset, py_value);
                }
            } else {
                instance.setattr(field.name_interned.bind(py), py_value)
                    .map_err(de::Error::custom)?;
            }
        }

        Ok(instance.unbind())
    }
}

struct ListVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    item_descriptor: &'a TypeDescriptor,
}

impl<'a, 'py, 'de> Visitor<'de> for ListVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a JSON array")
    }

    fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let py = self.ctx.py;
        let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
        let mut idx = 0usize;
        while let Some(item) = seq.next_element_seed(TypeDescriptorSeed {
            ctx: self.ctx,
            descriptor: self.item_descriptor,
        }).map_err(|e| {
            let inner = e.to_string();
            try_wrap_err_json(&idx.to_string(), &inner)
                .map(de::Error::custom)
                .unwrap_or(e)
        })? {
            items.push(item);
            idx += 1;
        }
        Ok(PyList::new(py, items).map_err(de::Error::custom)?.unbind().into())
    }
}

struct DictVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    value_descriptor: &'a TypeDescriptor,
}

impl<'a, 'py, 'de> Visitor<'de> for DictVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a JSON object")
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let py = self.ctx.py;
        let dict = PyDict::new(py);
        while let Some(key) = map.next_key::<&str>()? {
            let value = map.next_value_seed(TypeDescriptorSeed {
                ctx: self.ctx,
                descriptor: self.value_descriptor,
            }).map_err(|e| {
                let inner = e.to_string();
                try_wrap_err_json(key, &inner)
                    .map(de::Error::custom)
                    .unwrap_or(e)
            })?;
            dict.set_item(key, value).map_err(de::Error::custom)?;
        }
        Ok(dict.unbind().into())
    }
}

fn deserialize_dict_map<'a, 'py, 'de, A>(
    ctx: &'a StreamingContext<'a, 'py>,
    mut map: A,
    value_schema: &'a FieldDescriptor,
    field_name: &str,
) -> Result<Py<PyAny>, A::Error>
where
    A: MapAccess<'de>,
{
    let py = ctx.py;
    let dict = PyDict::new(py);
    while let Some(key) = map.next_key::<&str>()? {
        let value = map.next_value_seed(FieldDescriptorSeed {
            ctx,
            field: value_schema,
        }).map_err(|e| {
            let inner = e.to_string();
            try_wrap_err_json(key, &inner)
                .and_then(|wrapped| try_wrap_err_json(field_name, &wrapped))
                .map(de::Error::custom)
                .unwrap_or(e)
        })?;
        dict.set_item(key, value).map_err(de::Error::custom)?;
    }
    Ok(dict.unbind().into())
}

struct OptionalVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    inner_descriptor: Option<&'a TypeDescriptor>,
}

impl<'a, 'py, 'de> Visitor<'de> for OptionalVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("an optional value")
    }

    fn visit_none<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(self.ctx.py.None())
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(self.ctx.py.None())
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: de::Deserializer<'de>,
    {
        if let Some(inner) = self.inner_descriptor {
            TypeDescriptorSeed {
                ctx: self.ctx,
                descriptor: inner,
            }.deserialize(deserializer)
        } else {
            Err(de::Error::custom("Missing inner_type for optional"))
        }
    }
}

struct SetVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    item_descriptor: &'a TypeDescriptor,
}

impl<'a, 'py, 'de> Visitor<'de> for SetVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a JSON array for set")
    }

    fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let py = self.ctx.py;
        let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
        let mut idx = 0usize;
        while let Some(item) = seq.next_element_seed(TypeDescriptorSeed {
            ctx: self.ctx,
            descriptor: self.item_descriptor,
        }).map_err(|e| {
            let inner = e.to_string();
            try_wrap_err_json(&idx.to_string(), &inner)
                .map(de::Error::custom)
                .unwrap_or(e)
        })? {
            items.push(item);
            idx += 1;
        }
        Ok(PySet::new(py, &items).map_err(de::Error::custom)?.unbind().into())
    }
}

struct FrozenSetVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    item_descriptor: &'a TypeDescriptor,
}

impl<'a, 'py, 'de> Visitor<'de> for FrozenSetVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a JSON array for frozenset")
    }

    fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let py = self.ctx.py;
        let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
        let mut idx = 0usize;
        while let Some(item) = seq.next_element_seed(TypeDescriptorSeed {
            ctx: self.ctx,
            descriptor: self.item_descriptor,
        }).map_err(|e| {
            let inner = e.to_string();
            try_wrap_err_json(&idx.to_string(), &inner)
                .map(de::Error::custom)
                .unwrap_or(e)
        })? {
            items.push(item);
            idx += 1;
        }
        Ok(PyFrozenSet::new(py, &items).map_err(de::Error::custom)?.unbind().into())
    }
}

struct TupleVisitor<'a, 'py> {
    ctx: &'a StreamingContext<'a, 'py>,
    item_descriptor: &'a TypeDescriptor,
}

impl<'a, 'py, 'de> Visitor<'de> for TupleVisitor<'a, 'py> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a JSON array for tuple")
    }

    fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let py = self.ctx.py;
        let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
        let mut idx = 0usize;
        while let Some(item) = seq.next_element_seed(TypeDescriptorSeed {
            ctx: self.ctx,
            descriptor: self.item_descriptor,
        }).map_err(|e| {
            let inner = e.to_string();
            try_wrap_err_json(&idx.to_string(), &inner)
                .map(de::Error::custom)
                .unwrap_or(e)
        })? {
            items.push(item);
            idx += 1;
        }
        Ok(PyTuple::new(py, &items).map_err(de::Error::custom)?.unbind().into())
    }
}

fn deserialize_primitive_streaming<'de, D>(
    py: Python,
    deserializer: D,
    field_type: &FieldType,
) -> Result<Py<PyAny>, D::Error>
where
    D: de::Deserializer<'de>,
{
    struct PrimitiveVisitor<'py> {
        py: Python<'py>,
        field_type: FieldType,
    }

    impl<'py, 'de> Visitor<'de> for PrimitiveVisitor<'py> {
        type Value = Py<PyAny>;

        fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
            write!(formatter, "a primitive value of type {:?}", self.field_type)
        }

        fn visit_bool<E>(self, v: bool) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            Ok(v.into_py_any(self.py).map_err(de::Error::custom)?)
        }

        fn visit_i64<E>(self, v: i64) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            Ok(v.into_py_any(self.py).map_err(de::Error::custom)?)
        }

        fn visit_u64<E>(self, v: u64) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            Ok(v.into_py_any(self.py).map_err(de::Error::custom)?)
        }

        fn visit_f64<E>(self, v: f64) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            Ok(v.into_py_any(self.py).map_err(de::Error::custom)?)
        }

        fn visit_str<E>(self, v: &str) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            let py = self.py;
            match self.field_type {
                FieldType::Str => Ok(v.into_py_any(py).map_err(de::Error::custom)?),
                FieldType::Decimal => {
                    let cached = get_cached_types(py).map_err(de::Error::custom)?;
                    Ok(cached.decimal_cls.bind(py).call1((v,)).map_err(de::Error::custom)?.unbind())
                }
                FieldType::Uuid => {
                    let cached = get_cached_types(py).map_err(de::Error::custom)?;
                    let uuid = Uuid::parse_str(v).map_err(de::Error::custom)?;
                    cached.create_uuid_fast(py, uuid.as_u128()).map_err(de::Error::custom)
                }
                FieldType::DateTime => {
                    match parse_rfc3339_datetime(v) {
                        Some((year, month, day, hour, minute, second, microsecond, offset_seconds)) => {
                            create_pydatetime_with_offset(py, year, month, day, hour, minute, second, microsecond, offset_seconds)
                                .map_err(de::Error::custom)
                        }
                        None => Err(de::Error::custom("Not a valid datetime")),
                    }
                }
                FieldType::Date => {
                    match parse_iso_date(v) {
                        Some((year, month, day)) => {
                            PyDate::new(py, year, month, day)
                                .map(|d| d.into_any().unbind())
                                .map_err(de::Error::custom)
                        }
                        None => Err(de::Error::custom("Not a valid date")),
                    }
                }
                FieldType::Time => {
                    match parse_iso_time(v) {
                        Some((hour, minute, second, microsecond)) => {
                            PyTime::new(py, hour, minute, second, microsecond, None)
                                .map(|t| t.into_any().unbind())
                                .map_err(de::Error::custom)
                        }
                        None => Err(de::Error::custom("Not a valid time")),
                    }
                }
                FieldType::Any => Ok(v.into_py_any(py).map_err(de::Error::custom)?),
                _ => Err(de::Error::custom("Unexpected string for primitive type")),
            }
        }

        fn visit_unit<E>(self) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            Ok(self.py.None())
        }

        fn visit_none<E>(self) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            Ok(self.py.None())
        }

        fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
        where
            A: MapAccess<'de>,
        {
            // Handle serde_json arbitrary precision numbers
            if let Some(key) = map.next_key::<&str>()? {
                if key == SERDE_JSON_NUMBER_TOKEN {
                    let num_str: String = map.next_value()?;
                    let is_float = is_json_float_string(&num_str);

                    return match self.field_type {
                        FieldType::Int => {
                            if is_float {
                                Err(de::Error::custom("Not a valid integer"))
                            } else {
                                let cached = get_cached_types(self.py).map_err(de::Error::custom)?;
                                cached.int_cls.bind(self.py).call1((&num_str,))
                                    .map(|i| i.unbind())
                                    .map_err(de::Error::custom)
                            }
                        }
                        FieldType::Float => {
                            match num_str.parse::<f64>() {
                                Ok(f) => Ok(f.into_py_any(self.py).map_err(de::Error::custom)?),
                                Err(_) => Err(de::Error::custom("Not a valid float")),
                            }
                        }
                        FieldType::Decimal => {
                            let cached = get_cached_types(self.py).map_err(de::Error::custom)?;
                            cached.decimal_cls.bind(self.py).call1((&num_str,))
                                .map(|d| d.unbind())
                                .map_err(de::Error::custom)
                        }
                        _ => Err(de::Error::custom(format!(
                            "Unexpected map for primitive type {:?}",
                            self.field_type
                        ))),
                    };
                }
            }
            Err(de::Error::custom(format!(
                "Unexpected map for primitive type {:?}",
                self.field_type
            )))
        }
    }

    deserializer.deserialize_any(PrimitiveVisitor {
        py,
        field_type: field_type.clone(),
    })
}

pub fn load_from_bytes<'py>(
    py: Python<'py>,
    json_bytes: &[u8],
    descriptor: &TypeDescriptor,
    post_loads: Option<&Bound<'py, PyDict>>,
) -> PyResult<Py<PyAny>> {
    let ctx = StreamingContext {
        py,
        post_loads,
    };

    let mut deserializer = serde_json::Deserializer::from_slice(json_bytes);
    let result = TypeDescriptorSeed {
        ctx: &ctx,
        descriptor,
    }.deserialize(&mut deserializer);

    match result {
        Ok(value) => Ok(value),
        Err(e) => {
            let msg = strip_serde_locations(&e.to_string());
            let py_err = serde_json::from_str::<Value>(&msg)
                .ok()
                .and_then(|v| json_error_to_py(py, &v).ok())
                .unwrap_or_else(|| msg.clone().into_pyobject(py).unwrap().into_any().unbind());
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(py_err))
        }
    }
}
