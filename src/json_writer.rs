use std::fmt::Write;

use arrayvec::ArrayString;
use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use chrono::{DateTime, FixedOffset, NaiveDateTime};
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDict, PyFloat, PyInt, PyList, PyString};

use crate::container::{DataclassContainer, DataclassRegistry, FieldContainer, TypeContainer};
use crate::error::SerializationError;
use crate::fields::collection::CollectionKind;
use crate::fields::datetime::DateTimeFormat;
use crate::fields::decimal::get_decimal_cls;
use crate::fields::range::validate_range;
use crate::utils::call_validator;

fn write_json_string(buf: &mut Vec<u8>, s: &str) {
    buf.push(b'"');
    for byte in s.bytes() {
        match byte {
            b'"' => buf.extend_from_slice(b"\\\""),
            b'\\' => buf.extend_from_slice(b"\\\\"),
            b'\n' => buf.extend_from_slice(b"\\n"),
            b'\r' => buf.extend_from_slice(b"\\r"),
            b'\t' => buf.extend_from_slice(b"\\t"),
            b if b < 0x20 => {
                buf.extend_from_slice(b"\\u00");
                let hi = b >> 4;
                let lo = b & 0x0f;
                buf.push(if hi < 10 { b'0' + hi } else { b'a' + hi - 10 });
                buf.push(if lo < 10 { b'0' + lo } else { b'a' + lo - 10 });
            }
            _ => buf.push(byte),
        }
    }
    buf.push(b'"');
}

fn write_display_string<const N: usize, T: std::fmt::Display>(buf: &mut Vec<u8>, value: &T) {
    let mut arr = ArrayString::<N>::new();
    write!(&mut arr, "{value}").expect("buffer overflow");
    write_json_string(buf, &arr);
}

#[allow(clippy::cast_sign_loss, clippy::unused_self)]
impl FieldContainer {
    pub fn dump_to_json(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
        buf: &mut Vec<u8>,
    ) -> Result<(), SerializationError> {
        if value.is_none() {
            buf.extend_from_slice(b"null");
            return Ok(());
        }

        let common = self.common();
        match self {
            Self::Str {
                strip_whitespaces, ..
            } => {
                let py = value.py();
                let py_str = value
                    .cast::<PyString>()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                let s = py_str
                    .to_str()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                if *strip_whitespaces {
                    let trimmed = s.trim();
                    if trimmed.is_empty() && common.optional {
                        buf.extend_from_slice(b"null");
                    } else {
                        write_json_string(buf, trimmed);
                    }
                } else {
                    write_json_string(buf, s);
                }
                Ok(())
            }
            Self::Int {
                gt, gte, lt, lte, ..
            } => {
                let py = value.py();
                if !value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                validate_range(value, gt.as_ref(), gte.as_ref(), lt.as_ref(), lte.as_ref())?;
                if let Ok(i) = value.extract::<i64>() {
                    buf.extend_from_slice(itoa::Buffer::new().format(i).as_bytes());
                } else {
                    let s = value
                        .str()
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    let s = s
                        .to_str()
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    buf.extend_from_slice(s.as_bytes());
                }
                Ok(())
            }
            Self::Float {
                gt, gte, lt, lte, ..
            } => {
                let py = value.py();
                if value.is_instance_of::<PyBool>() {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                if !value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyFloat>() {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let f: f64 = value
                    .extract()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                if f.is_nan() || f.is_infinite() {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                validate_range(value, gt.as_ref(), gte.as_ref(), lt.as_ref(), lte.as_ref())?;
                buf.extend_from_slice(ryu::Buffer::new().format(f).as_bytes());
                Ok(())
            }
            Self::Bool { .. } => {
                let py = value.py();
                if !value.is_instance_of::<PyBool>() {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let b: bool = value.extract().unwrap();
                buf.extend_from_slice(if b { b"true" } else { b"false" });
                Ok(())
            }
            Self::Decimal {
                decimal_places,
                rounding,
                gt,
                gte,
                lt,
                lte,
                ..
            } => {
                let py = value.py();
                let decimal_cls = get_decimal_cls(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                if !value
                    .is_instance(decimal_cls)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?
                {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let is_finite: bool = value
                    .call_method0(intern!(py, "is_finite"))
                    .and_then(|v| v.extract())
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                if !is_finite {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let decimal = if let Some(places) = decimal_places {
                    if let Some(rounding) = rounding {
                        let exp =
                            crate::fields::decimal::get_quantize_exp(py, places.unsigned_abs())
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                        value
                            .call_method1(intern!(py, "quantize"), (&exp, rounding.bind(py)))
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))?
                    } else {
                        value.clone()
                    }
                } else {
                    value.clone()
                };
                validate_range(
                    &decimal,
                    gt.as_ref(),
                    gte.as_ref(),
                    lt.as_ref(),
                    lte.as_ref(),
                )?;
                let formatted = decimal
                    .call_method1(intern!(py, "__format__"), ("f",))
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                let s = formatted
                    .cast::<PyString>()
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                let s = s
                    .to_str()
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                write_json_string(buf, s);
                Ok(())
            }
            Self::Date { .. } => {
                let py = value.py();
                let date: chrono::NaiveDate = value
                    .extract()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                write_display_string::<16, _>(buf, &date);
                Ok(())
            }
            Self::Time { .. } => {
                let py = value.py();
                let time: chrono::NaiveTime = value
                    .extract()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                write_display_string::<16, _>(buf, &time);
                Ok(())
            }
            Self::DateTime { format, .. } => {
                let py = value.py();
                let dt = extract_datetime(value)
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                match format {
                    DateTimeFormat::Iso => {
                        write_display_string::<40, _>(buf, &dt.format("%+"));
                    }
                    DateTimeFormat::Timestamp => {
                        let micros = dt.timestamp_micros();
                        if micros < 0 {
                            return Err(SerializationError::Single(
                                common.invalid_error.clone_ref(py),
                            ));
                        }
                        #[allow(clippy::cast_precision_loss)]
                        let ts = micros as f64 / 1_000_000.0;
                        buf.extend_from_slice(ryu::Buffer::new().format(ts).as_bytes());
                    }
                    DateTimeFormat::Strftime(chrono_fmt) => {
                        let formatted = dt.format(chrono_fmt).to_string();
                        write_json_string(buf, &formatted);
                    }
                }
                Ok(())
            }
            Self::Uuid { .. } => {
                let py = value.py();
                let uuid: ::uuid::Uuid = value
                    .extract()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                buf.push(b'"');
                let mut uuid_buf = [0u8; 36];
                uuid.as_hyphenated().encode_lower(&mut uuid_buf);
                buf.extend_from_slice(&uuid_buf);
                buf.push(b'"');
                Ok(())
            }
            Self::Bytes { .. } => {
                let py = value.py();
                if !value.is_instance_of::<PyBytes>() {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let bytes: &[u8] = value.extract().expect("already checked type");
                buf.push(b'"');
                let encoded = STANDARD.encode(bytes);
                buf.extend_from_slice(encoded.as_bytes());
                buf.push(b'"');
                Ok(())
            }
            Self::IntEnum {
                common,
                dumper_data,
                ..
            } => {
                let py = value.py();
                if !value
                    .is_instance(dumper_data.enum_cls.bind(py))
                    .unwrap_or(false)
                {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let enum_value = value
                    .getattr("value")
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                if let Ok(i) = enum_value.extract::<i64>() {
                    buf.extend_from_slice(itoa::Buffer::new().format(i).as_bytes());
                } else {
                    let s = enum_value
                        .str()
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    let s = s
                        .to_str()
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    buf.extend_from_slice(s.as_bytes());
                }
                Ok(())
            }
            Self::StrEnum {
                common,
                dumper_data,
                ..
            } => {
                let py = value.py();
                if !value
                    .is_instance(dumper_data.enum_cls.bind(py))
                    .unwrap_or(false)
                {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let enum_value = value
                    .getattr("value")
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                let s = enum_value
                    .cast::<PyString>()
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                let s = s
                    .to_str()
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                write_json_string(buf, s);
                Ok(())
            }
            Self::StrLiteral { common, data } => {
                let py = value.py();
                if let Ok(py_str) = value.cast::<PyString>()
                    && let Ok(s) = py_str.to_str()
                {
                    for allowed in &data.values {
                        if allowed == s {
                            write_json_string(buf, s);
                            return Ok(());
                        }
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::IntLiteral { common, data } => {
                let py = value.py();
                if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
                    for allowed in &data.values {
                        if value.eq(allowed.bind(py)).unwrap_or(false) {
                            if let Ok(i) = value.extract::<i64>() {
                                buf.extend_from_slice(itoa::Buffer::new().format(i).as_bytes());
                            } else {
                                let s = value
                                    .str()
                                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                                let s = s
                                    .to_str()
                                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                                buf.extend_from_slice(s.as_bytes());
                            }
                            return Ok(());
                        }
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::BoolLiteral { common, data } => {
                let py = value.py();
                if value.is_instance_of::<PyBool>()
                    && let Ok(b) = value.extract::<bool>()
                {
                    for &allowed in &data.values {
                        if b == allowed {
                            buf.extend_from_slice(if b { b"true" } else { b"false" });
                            return Ok(());
                        }
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::Any { .. } => write_any_to_json(value, buf),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => dump_collection_to_json(
                registry,
                value,
                *kind,
                item,
                item_validator.as_ref(),
                &common.invalid_error,
                buf,
            ),
            Self::Dict {
                value: value_schema,
                value_validator,
                ..
            } => dump_dict_field_to_json(
                registry,
                value,
                value_schema,
                value_validator.as_ref(),
                &common.invalid_error,
                buf,
            ),
            Self::Nested {
                dataclass_index, ..
            } => registry
                .get(*dataclass_index)
                .dump_to_json(registry, value, buf),
            Self::Union { variants, .. } => {
                let py = value.py();
                for variant in variants {
                    let checkpoint = buf.len();
                    if variant.dump_to_json(registry, value, buf).is_ok() {
                        return Ok(());
                    }
                    buf.truncate(checkpoint);
                }
                Err(SerializationError::Single(
                    intern!(py, "Value does not match any union variant")
                        .clone()
                        .unbind(),
                ))
            }
        }
    }
}

impl DataclassContainer {
    pub fn dump_to_json(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
        buf: &mut Vec<u8>,
    ) -> Result<(), SerializationError> {
        let py = value.py();

        if !value.is_instance(self.cls.bind(py)).unwrap_or(false) {
            return Err(SerializationError::Single(
                intern!(
                    py,
                    "Invalid nested object type. Expected instance of dataclass."
                )
                .clone()
                .unbind(),
            ));
        }

        let missing_sentinel = crate::utils::get_missing_sentinel(py)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        buf.push(b'{');
        let mut first = true;

        for dc_field in &self.fields {
            let common = dc_field.field.common();

            let py_value = match dc_field.slot_offset {
                Some(offset) => {
                    match unsafe { crate::slots::get_slot_value_direct(py, value, offset) } {
                        Some(v) => v,
                        None => value
                            .getattr(dc_field.name_interned.bind(py))
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))?,
                    }
                }
                None => value
                    .getattr(dc_field.name_interned.bind(py))
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?,
            };

            if py_value.is(missing_sentinel.as_any()) || (py_value.is_none() && self.ignore_none) {
                continue;
            }

            if let Some(ref validator) = common.validator
                && let Ok(Some(_err_list)) = call_validator(py, validator, &py_value)
            {
                continue;
            }

            if !first {
                buf.push(b',');
            }
            first = false;

            write_json_string(buf, &dc_field.data_key);

            buf.push(b':');

            if py_value.is_none() {
                buf.extend_from_slice(b"null");
            } else {
                dc_field.field.dump_to_json(registry, &py_value, buf)?;
            }
        }

        buf.push(b'}');
        Ok(())
    }
}

impl TypeContainer {
    pub fn dump_to_json(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
        buf: &mut Vec<u8>,
    ) -> Result<(), SerializationError> {
        let py = value.py();

        match self {
            Self::Dataclass(idx) => registry.get(*idx).dump_to_json(registry, value, buf),
            Self::Primitive(p) => {
                if value.is_none() {
                    buf.extend_from_slice(b"null");
                    return Ok(());
                }
                p.field.dump_to_json(registry, value, buf)
            }
            Self::List { item } => {
                let list = value.cast::<PyList>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a list").clone().unbind())
                })?;
                buf.push(b'[');
                for (idx, v) in list.iter().enumerate() {
                    if idx > 0 {
                        buf.push(b',');
                    }
                    item.dump_to_json(registry, &v, buf)?;
                }
                buf.push(b']');
                Ok(())
            }
            Self::Dict {
                value: value_container,
            } => {
                let dict = value.cast::<PyDict>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a dict").clone().unbind())
                })?;
                buf.push(b'{');
                let mut first = true;
                for (k, v) in dict.iter() {
                    if !first {
                        buf.push(b',');
                    }
                    first = false;
                    let key_str = k
                        .cast::<PyString>()
                        .map_err(|_| SerializationError::simple(py, "Dict key must be a string"))?;
                    let key = key_str
                        .to_str()
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    write_json_string(buf, key);
                    buf.push(b':');
                    value_container.dump_to_json(registry, &v, buf)?;
                }
                buf.push(b'}');
                Ok(())
            }
            Self::Optional { inner } => {
                if value.is_none() {
                    buf.extend_from_slice(b"null");
                    Ok(())
                } else {
                    inner.dump_to_json(registry, value, buf)
                }
            }
            Self::Set { item } | Self::FrozenSet { item } | Self::Tuple { item } => {
                let iter = value.try_iter().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected an iterable").clone().unbind())
                })?;
                buf.push(b'[');
                let mut first = true;
                for item_result in iter {
                    let v =
                        item_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    if !first {
                        buf.push(b',');
                    }
                    first = false;
                    item.dump_to_json(registry, &v, buf)?;
                }
                buf.push(b']');
                Ok(())
            }
            Self::Union { variants } => {
                for variant in variants {
                    let checkpoint = buf.len();
                    if variant.dump_to_json(registry, value, buf).is_ok() {
                        return Ok(());
                    }
                    buf.truncate(checkpoint);
                }
                Err(SerializationError::Single(
                    intern!(py, "Value does not match any union variant")
                        .clone()
                        .unbind(),
                ))
            }
        }
    }
}

fn extract_datetime(value: &Bound<'_, PyAny>) -> PyResult<DateTime<FixedOffset>> {
    if let Ok(dt) = value.extract::<DateTime<FixedOffset>>() {
        return Ok(dt);
    }
    let naive: NaiveDateTime = value.extract()?;
    Ok(naive.and_utc().fixed_offset())
}

fn write_any_to_json(
    value: &Bound<'_, PyAny>,
    buf: &mut Vec<u8>,
) -> Result<(), SerializationError> {
    let py = value.py();

    if value.is_none() {
        buf.extend_from_slice(b"null");
        return Ok(());
    }
    if value.is_instance_of::<PyBool>() {
        let b: bool = value.extract().unwrap();
        buf.extend_from_slice(if b { b"true" } else { b"false" });
        return Ok(());
    }
    if value.is_instance_of::<PyInt>() {
        if let Ok(i) = value.extract::<i64>() {
            buf.extend_from_slice(itoa::Buffer::new().format(i).as_bytes());
        } else {
            let s = value
                .str()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            let s = s
                .to_str()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            buf.extend_from_slice(s.as_bytes());
        }
        return Ok(());
    }
    if value.is_instance_of::<PyFloat>() {
        let f: f64 = value
            .extract()
            .map_err(|_| SerializationError::simple(py, "Not a valid JSON-serializable value."))?;
        if f.is_nan() || f.is_infinite() {
            return Err(SerializationError::simple(
                py,
                "Not a valid JSON-serializable value.",
            ));
        }
        buf.extend_from_slice(ryu::Buffer::new().format(f).as_bytes());
        return Ok(());
    }
    if value.is_instance_of::<PyString>() {
        let s: &str = value
            .extract()
            .map_err(|_| SerializationError::simple(py, "Not a valid JSON-serializable value."))?;
        write_json_string(buf, s);
        return Ok(());
    }
    if let Ok(list) = value.cast::<PyList>() {
        buf.push(b'[');
        for (idx, v) in list.iter().enumerate() {
            if idx > 0 {
                buf.push(b',');
            }
            write_any_to_json(&v, buf)?;
        }
        buf.push(b']');
        return Ok(());
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        buf.push(b'{');
        let mut first = true;
        for (k, v) in dict.iter() {
            if !k.is_instance_of::<PyString>() {
                return Err(SerializationError::simple(
                    py,
                    "Not a valid JSON-serializable value.",
                ));
            }
            if !first {
                buf.push(b',');
            }
            first = false;
            let key: &str = k.extract().map_err(|_| {
                SerializationError::simple(py, "Not a valid JSON-serializable value.")
            })?;
            write_json_string(buf, key);
            buf.push(b':');
            write_any_to_json(&v, buf)?;
        }
        buf.push(b'}');
        return Ok(());
    }

    Err(SerializationError::simple(
        py,
        "Not a valid JSON-serializable value.",
    ))
}

fn dump_collection_to_json(
    registry: &DataclassRegistry,
    value: &Bound<'_, PyAny>,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
    buf: &mut Vec<u8>,
) -> Result<(), SerializationError> {
    let py = value.py();
    if !kind.is_valid_type(value) {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }
    let iter = value
        .try_iter()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
    buf.push(b'[');
    let mut first = true;
    for item_result in iter {
        let item_value = item_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if let Some(validator) = item_validator
            && let Ok(Some(_err_list)) = call_validator(py, validator, &item_value)
        {
            continue;
        }
        if !first {
            buf.push(b',');
        }
        first = false;
        item.dump_to_json(registry, &item_value, buf)?;
    }
    buf.push(b']');
    Ok(())
}

fn dump_dict_field_to_json(
    registry: &DataclassRegistry,
    value: &Bound<'_, PyAny>,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
    buf: &mut Vec<u8>,
) -> Result<(), SerializationError> {
    let py = value.py();
    let dict = value
        .cast::<PyDict>()
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
    buf.push(b'{');
    let mut first = true;
    for (k, v) in dict.iter() {
        let key_str = k
            .cast::<PyString>()
            .map_err(|_| {
                SerializationError::Single(
                    intern!(py, "Dict key must be a string").clone().unbind(),
                )
            })?
            .to_str()
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if let Some(validator) = value_validator
            && let Ok(Some(_err_list)) = call_validator(py, validator, &v)
        {
            continue;
        }
        if !first {
            buf.push(b',');
        }
        first = false;
        write_json_string(buf, key_str);
        buf.push(b':');
        value_schema.dump_to_json(registry, &v, buf)?;
    }
    buf.push(b'}');
    Ok(())
}
