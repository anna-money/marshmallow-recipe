use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDict, PyFrozenSet, PyList, PySet, PyString, PyTuple};
use smallbitvec::SmallBitVec;

use crate::container::{
    DataclassContainer, DataclassRegistry, FieldCommon, FieldContainer, TypeContainer,
};
use crate::error::{SerializationError, accumulate_error};
use crate::fields::collection::CollectionKind;
use crate::fields::datetime::DateTimeFormat;
use crate::fields::decimal::{get_decimal_cls, get_quantize_exp};
use crate::fields::range::validate_range;
use crate::slots::set_slot_value_direct;
use crate::utils::{call_validator, get_object_cls, new_presized_list, parse_datetime_with_format};

use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use chrono::{DateTime, FixedOffset, NaiveDateTime, NaiveTime};
use pyo3::conversion::IntoPyObjectExt;

const NESTED_ERROR: &str = "Invalid input type.";

fn skip_whitespace(bytes: &[u8], pos: &mut usize) {
    while *pos < bytes.len() && bytes[*pos].is_ascii_whitespace() {
        *pos += 1;
    }
}

fn expect_char(bytes: &[u8], pos: &mut usize, ch: u8) -> bool {
    skip_whitespace(bytes, pos);
    if *pos < bytes.len() && bytes[*pos] == ch {
        *pos += 1;
        true
    } else {
        false
    }
}

fn peek_char(bytes: &[u8], pos: &mut usize) -> Option<u8> {
    skip_whitespace(bytes, pos);
    bytes.get(*pos).copied()
}

fn read_json_string<'a>(bytes: &'a [u8], pos: &mut usize) -> Option<std::borrow::Cow<'a, str>> {
    skip_whitespace(bytes, pos);
    if *pos >= bytes.len() || bytes[*pos] != b'"' {
        return None;
    }
    *pos += 1;
    let start = *pos;

    if let Some(end_offset) = memchr::memchr2(b'"', b'\\', &bytes[start..]) {
        let end = start + end_offset;
        if bytes[end] == b'"' {
            let s = std::str::from_utf8(&bytes[start..end]).ok()?;
            *pos = end + 1;
            return Some(std::borrow::Cow::Borrowed(s));
        }
    }

    let mut has_escape = false;
    while *pos < bytes.len() {
        match bytes[*pos] {
            b'"' => {
                let result = if has_escape {
                    let s = &bytes[start..*pos];
                    let unescaped = unescape_json_string(s)?;
                    std::borrow::Cow::Owned(unescaped)
                } else {
                    let s = std::str::from_utf8(&bytes[start..*pos]).ok()?;
                    std::borrow::Cow::Borrowed(s)
                };
                *pos += 1;
                return Some(result);
            }
            b'\\' => {
                has_escape = true;
                *pos += 1;
                if *pos < bytes.len() {
                    *pos += 1;
                }
            }
            _ => *pos += 1,
        }
    }
    None
}

fn unescape_json_string(bytes: &[u8]) -> Option<String> {
    let mut result = String::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'\\' {
            i += 1;
            if i >= bytes.len() {
                return None;
            }
            match bytes[i] {
                b'"' => result.push('"'),
                b'\\' => result.push('\\'),
                b'/' => result.push('/'),
                b'n' => result.push('\n'),
                b'r' => result.push('\r'),
                b't' => result.push('\t'),
                b'b' => result.push('\u{0008}'),
                b'f' => result.push('\u{000C}'),
                b'u' => {
                    if i + 4 >= bytes.len() {
                        return None;
                    }
                    let hex = std::str::from_utf8(&bytes[i + 1..i + 5]).ok()?;
                    let code = u16::from_str_radix(hex, 16).ok()?;
                    if let Some(ch) = char::from_u32(code.into()) {
                        result.push(ch);
                    }
                    i += 4;
                }
                _ => return None,
            }
        } else {
            result.push(bytes[i] as char);
        }
        i += 1;
    }
    Some(result)
}

fn read_json_number<'a>(bytes: &'a [u8], pos: &mut usize) -> Option<&'a str> {
    skip_whitespace(bytes, pos);
    let start = *pos;
    while *pos < bytes.len() {
        match bytes[*pos] {
            b'0'..=b'9' | b'-' | b'+' | b'.' | b'e' | b'E' => *pos += 1,
            _ => break,
        }
    }
    if *pos > start {
        std::str::from_utf8(&bytes[start..*pos]).ok()
    } else {
        None
    }
}

fn skip_json_value(bytes: &[u8], pos: &mut usize) -> bool {
    skip_whitespace(bytes, pos);
    if *pos >= bytes.len() {
        return false;
    }
    match bytes[*pos] {
        b'"' => read_json_string(bytes, pos).is_some(),
        b'{' => {
            *pos += 1;
            if peek_char(bytes, pos) == Some(b'}') {
                *pos += 1;
                return true;
            }
            loop {
                if read_json_string(bytes, pos).is_none() {
                    return false;
                }
                if !expect_char(bytes, pos, b':') {
                    return false;
                }
                if !skip_json_value(bytes, pos) {
                    return false;
                }
                if peek_char(bytes, pos) == Some(b'}') {
                    *pos += 1;
                    return true;
                }
                if !expect_char(bytes, pos, b',') {
                    return false;
                }
            }
        }
        b'[' => {
            *pos += 1;
            if peek_char(bytes, pos) == Some(b']') {
                *pos += 1;
                return true;
            }
            loop {
                if !skip_json_value(bytes, pos) {
                    return false;
                }
                if peek_char(bytes, pos) == Some(b']') {
                    *pos += 1;
                    return true;
                }
                if !expect_char(bytes, pos, b',') {
                    return false;
                }
            }
        }
        b't' => {
            if bytes[*pos..].starts_with(b"true") {
                *pos += 4;
                true
            } else {
                false
            }
        }
        b'f' => {
            if bytes[*pos..].starts_with(b"false") {
                *pos += 5;
                true
            } else {
                false
            }
        }
        b'n' => {
            if bytes[*pos..].starts_with(b"null") {
                *pos += 4;
                true
            } else {
                false
            }
        }
        b'0'..=b'9' | b'-' => read_json_number(bytes, pos).is_some(),
        _ => false,
    }
}

fn apply_validate(
    py: Python<'_>,
    value: Py<PyAny>,
    validator: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, SerializationError> {
    if let Some(validator) = validator {
        match call_validator(py, validator, value.bind(py)) {
            Ok(None) => {}
            Ok(Some(errors)) => {
                return Err(crate::error::pyerrors_to_serialization_error(py, &errors));
            }
            Err(e) => {
                let error_value = crate::utils::extract_error_args(py, &e);
                return Err(crate::error::pyerrors_to_serialization_error(
                    py,
                    &error_value,
                ));
            }
        }
    }
    Ok(value)
}

fn get_default_value(
    py: Python<'_>,
    common: &FieldCommon,
) -> Result<Option<Py<PyAny>>, SerializationError> {
    if let Some(ref factory) = common.default_factory {
        return factory
            .call0(py)
            .map(Some)
            .map_err(|e| SerializationError::simple(py, &e.to_string()));
    }
    if let Some(ref value) = common.default_value {
        return Ok(Some(value.clone_ref(py)));
    }
    Ok(common.optional.then(|| py.None()))
}

fn parse_error(py: Python<'_>, invalid_error: &Py<PyString>) -> SerializationError {
    SerializationError::Single(invalid_error.clone_ref(py))
}

#[allow(clippy::cast_sign_loss)]
impl FieldContainer {
    pub fn load_from_json_bytes(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        bytes: &[u8],
        pos: &mut usize,
    ) -> Result<Py<PyAny>, SerializationError> {
        let common = self.common();

        skip_whitespace(bytes, pos);
        if *pos + 3 < bytes.len() && &bytes[*pos..*pos + 4] == b"null" {
            *pos += 4;
            if common.optional {
                return Ok(py.None());
            }
            return Err(common.none_error.as_ref().map_or_else(
                || {
                    SerializationError::Single(
                        intern!(py, "Field may not be null.").clone().unbind(),
                    )
                },
                |s| SerializationError::Single(s.clone_ref(py)),
            ));
        }

        match self {
            Self::Str {
                strip_whitespaces,
                post_load,
                ..
            } => {
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                if *strip_whitespaces {
                    let trimmed = s.trim();
                    if trimmed.is_empty() && common.optional {
                        return Ok(py.None());
                    }
                    let result: Py<PyAny> = PyString::new(py, trimmed).into_any().unbind();
                    if let Some(post_load) = post_load {
                        return post_load
                            .call1(py, (result.bind(py),))
                            .map_err(|e| SerializationError::simple(py, &e.to_string()));
                    }
                    Ok(result)
                } else {
                    let result: Py<PyAny> = PyString::new(py, &s).into_any().unbind();
                    if let Some(post_load) = post_load {
                        return post_load
                            .call1(py, (result.bind(py),))
                            .map_err(|e| SerializationError::simple(py, &e.to_string()));
                    }
                    Ok(result)
                }
            }
            Self::Int {
                gt, gte, lt, lte, ..
            } => {
                let num_str = read_json_number(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let i: i64 = num_str
                    .parse()
                    .map_err(|_| parse_error(py, &common.invalid_error))?;
                let result = i
                    .into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                validate_range(
                    result.bind(py),
                    gt.as_ref(),
                    gte.as_ref(),
                    lt.as_ref(),
                    lte.as_ref(),
                )?;
                Ok(result)
            }
            Self::Float {
                gt, gte, lt, lte, ..
            } => {
                let num_str = read_json_number(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let f: f64 = num_str
                    .parse()
                    .map_err(|_| parse_error(py, &common.invalid_error))?;
                if f.is_nan() || f.is_infinite() {
                    return Err(parse_error(py, &common.invalid_error));
                }
                let result = f
                    .into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                validate_range(
                    result.bind(py),
                    gt.as_ref(),
                    gte.as_ref(),
                    lt.as_ref(),
                    lte.as_ref(),
                )?;
                Ok(result)
            }
            Self::Bool { .. } => {
                skip_whitespace(bytes, pos);
                if bytes[*pos..].starts_with(b"true") {
                    *pos += 4;
                    Ok(PyBool::new(py, true).to_owned().into_any().unbind())
                } else if bytes[*pos..].starts_with(b"false") {
                    *pos += 5;
                    Ok(PyBool::new(py, false).to_owned().into_any().unbind())
                } else {
                    Err(parse_error(py, &common.invalid_error))
                }
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
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let decimal_cls = get_decimal_cls(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                let py_decimal = decimal_cls
                    .call1((&*s,))
                    .map_err(|_| parse_error(py, &common.invalid_error))?;
                let result = if let Some(places) = decimal_places
                    && let Some(rounding) = rounding
                {
                    let exp = get_quantize_exp(py, places.cast_unsigned())
                        .map_err(|_| parse_error(py, &common.invalid_error))?;
                    py_decimal
                        .call_method1(intern!(py, "quantize"), (&exp, rounding.bind(py)))
                        .map(Bound::unbind)
                        .map_err(|_| parse_error(py, &common.invalid_error))?
                } else {
                    py_decimal.unbind()
                };
                validate_range(
                    result.bind(py),
                    gt.as_ref(),
                    gte.as_ref(),
                    lt.as_ref(),
                    lte.as_ref(),
                )?;
                Ok(result)
            }
            Self::Date { .. } => {
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let date: chrono::NaiveDate = s
                    .parse()
                    .map_err(|_| parse_error(py, &common.invalid_error))?;
                date.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            }
            Self::Time { .. } => {
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let time: NaiveTime = s
                    .parse()
                    .map_err(|_| parse_error(py, &common.invalid_error))?;
                time.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            }
            Self::DateTime { format, .. } => match format {
                DateTimeFormat::Iso => {
                    let s = read_json_string(bytes, pos)
                        .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                    let dt = DateTime::<FixedOffset>::parse_from_rfc3339(&s).or_else(|_| {
                        NaiveDateTime::parse_from_str(&s, "%Y-%m-%dT%H:%M:%S")
                            .or_else(|_| NaiveDateTime::parse_from_str(&s, "%Y-%m-%dT%H:%M:%S%.f"))
                            .map(|naive| naive.and_utc().fixed_offset())
                    });
                    dt.map_err(|_| parse_error(py, &common.invalid_error))
                        .and_then(|dt| {
                            dt.into_py_any(py)
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))
                        })
                }
                DateTimeFormat::Timestamp => {
                    let num_str = read_json_number(bytes, pos)
                        .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                    let f: f64 = num_str
                        .parse()
                        .map_err(|_| parse_error(py, &common.invalid_error))?;
                    crate::fields::datetime::timestamp_to_datetime(f)
                        .ok_or_else(|| parse_error(py, &common.invalid_error))
                        .and_then(|dt| {
                            dt.into_py_any(py)
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))
                        })
                }
                DateTimeFormat::Strftime(chrono_fmt) => {
                    let s = read_json_string(bytes, pos)
                        .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                    parse_datetime_with_format(&s, chrono_fmt)
                        .ok_or_else(|| parse_error(py, &common.invalid_error))
                        .and_then(|dt| {
                            dt.into_py_any(py)
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))
                        })
                }
            },
            Self::Uuid { .. } => {
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                ::uuid::Uuid::parse_str(&s)
                    .map_err(|_| parse_error(py, &common.invalid_error))
                    .and_then(|u| {
                        u.into_pyobject(py)
                            .map(|b| b.into_any().unbind())
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))
                    })
            }
            Self::Bytes { .. } => {
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let input = s.as_bytes();
                let padding = input.iter().rev().take(2).filter(|&&b| b == b'=').count();
                let decoded_len = (input.len() / 4 * 3).saturating_sub(padding);
                PyBytes::new_with(py, decoded_len, |buf| {
                    STANDARD
                        .decode_slice(s.as_bytes(), buf)
                        .map(|_| ())
                        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
                })
                .map(|b| b.into_any().unbind())
                .map_err(|_| parse_error(py, &common.invalid_error))
            }
            Self::StrEnum {
                common,
                loader_data,
                ..
            } => {
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                for (k, member) in &loader_data.values {
                    if k == s.as_ref() {
                        return Ok(member.clone_ref(py));
                    }
                }
                Err(parse_error(py, &common.invalid_error))
            }
            Self::IntEnum {
                common,
                loader_data,
                ..
            } => {
                let num_str = read_json_number(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let n: i64 = num_str
                    .parse()
                    .map_err(|_| parse_error(py, &common.invalid_error))?;
                let py_n = n
                    .into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                for (k, member) in &loader_data.values {
                    if py_n.bind(py).eq(k.bind(py)).unwrap_or(false) {
                        return Ok(member.clone_ref(py));
                    }
                }
                Err(parse_error(py, &common.invalid_error))
            }
            Self::StrLiteral { common, data } => {
                let s = read_json_string(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                for allowed in &data.values {
                    if allowed == s.as_ref() {
                        return Ok(PyString::new(py, &s).into_any().unbind());
                    }
                }
                Err(parse_error(py, &common.invalid_error))
            }
            Self::IntLiteral { common, data } => {
                let num_str = read_json_number(bytes, pos)
                    .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                let n: i64 = num_str
                    .parse()
                    .map_err(|_| parse_error(py, &common.invalid_error))?;
                let py_n = n
                    .into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                for allowed in &data.values {
                    if py_n.bind(py).eq(allowed.bind(py)).unwrap_or(false) {
                        return Ok(py_n);
                    }
                }
                Err(parse_error(py, &common.invalid_error))
            }
            Self::BoolLiteral { common, data } => {
                skip_whitespace(bytes, pos);
                let b = if bytes[*pos..].starts_with(b"true") {
                    *pos += 4;
                    true
                } else if bytes[*pos..].starts_with(b"false") {
                    *pos += 5;
                    false
                } else {
                    return Err(parse_error(py, &common.invalid_error));
                };
                for &allowed in &data.values {
                    if b == allowed {
                        return Ok(PyBool::new(py, b).to_owned().into_any().unbind());
                    }
                }
                Err(parse_error(py, &common.invalid_error))
            }
            Self::Any { .. } => parse_any_json_value(py, bytes, pos),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => {
                if !expect_char(bytes, pos, b'[') {
                    return Err(parse_error(py, &common.invalid_error));
                }
                let mut items = Vec::new();
                let mut errors: Option<Bound<'_, PyDict>> = None;
                if peek_char(bytes, pos) != Some(b']') {
                    let mut idx = 0;
                    loop {
                        skip_whitespace(bytes, pos);
                        if bytes[*pos..].starts_with(b"null") {
                            *pos += 4;
                            items.push(py.None());
                        } else {
                            match item.load_from_json_bytes(py, registry, bytes, pos) {
                                Ok(py_val) => {
                                    if let Some(validator) = item_validator
                                        && let Ok(Some(err_list)) =
                                            call_validator(py, validator, py_val.bind(py))
                                    {
                                        let e = crate::error::pyerrors_to_serialization_error(
                                            py, &err_list,
                                        );
                                        accumulate_error(py, &mut errors, idx, &e);
                                    } else {
                                        items.push(py_val);
                                    }
                                }
                                Err(ref e) => accumulate_error(py, &mut errors, idx, e),
                            }
                        }
                        idx += 1;
                        if !expect_char(bytes, pos, b',') {
                            break;
                        }
                    }
                }
                if !expect_char(bytes, pos, b']') {
                    return Err(parse_error(py, &common.invalid_error));
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
            Self::Dict {
                value: value_schema,
                value_validator,
                ..
            } => {
                if !expect_char(bytes, pos, b'{') {
                    return Err(parse_error(py, &common.invalid_error));
                }
                let result = PyDict::new(py);
                let mut errors: Option<Bound<'_, PyDict>> = None;
                if peek_char(bytes, pos) != Some(b'}') {
                    loop {
                        let key = read_json_string(bytes, pos)
                            .ok_or_else(|| parse_error(py, &common.invalid_error))?;
                        if !expect_char(bytes, pos, b':') {
                            return Err(parse_error(py, &common.invalid_error));
                        }
                        skip_whitespace(bytes, pos);
                        if bytes[*pos..].starts_with(b"null") {
                            *pos += 4;
                            let _ = result.set_item(&*key, py.None());
                        } else {
                            match value_schema.load_from_json_bytes(py, registry, bytes, pos) {
                                Ok(py_val) => {
                                    if let Some(validator) = value_validator
                                        && let Ok(Some(err_list)) =
                                            call_validator(py, validator, py_val.bind(py))
                                    {
                                        let e = crate::error::pyerrors_to_serialization_error(
                                            py, &err_list,
                                        );
                                        accumulate_error(py, &mut errors, key.as_ref(), &e);
                                    } else {
                                        let _ = result.set_item(&*key, py_val);
                                    }
                                }
                                Err(e) => {
                                    let nested_dict = PyDict::new(py);
                                    let _ = nested_dict.set_item(
                                        "value",
                                        e.to_py_value(py).unwrap_or_else(|_| py.None()),
                                    );
                                    let wrapped = SerializationError::Dict(nested_dict.unbind());
                                    accumulate_error(py, &mut errors, key.as_ref(), &wrapped);
                                }
                            }
                        }
                        if !expect_char(bytes, pos, b',') {
                            break;
                        }
                    }
                }
                if !expect_char(bytes, pos, b'}') {
                    return Err(parse_error(py, &common.invalid_error));
                }
                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }
                Ok(result.into_any().unbind())
            }
            Self::Nested {
                dataclass_index, ..
            } => registry
                .get(*dataclass_index)
                .load_from_json_bytes(py, registry, bytes, pos),
            Self::Union { variants, .. } => {
                let checkpoint = *pos;
                let mut errors = Vec::new();
                for variant in variants {
                    *pos = checkpoint;
                    match variant.load_from_json_bytes(py, registry, bytes, pos) {
                        Ok(result) => return Ok(result),
                        Err(e) => errors.push(e),
                    }
                }
                Err(SerializationError::collect_list(py, errors))
            }
        }
    }
}

impl DataclassContainer {
    pub fn load_from_json_bytes(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        bytes: &[u8],
        pos: &mut usize,
    ) -> Result<Py<PyAny>, SerializationError> {
        if !expect_char(bytes, pos, b'{') {
            let err_dict = PyDict::new(py);
            let _ = err_dict.set_item(
                "_schema",
                PyList::new(py, [intern!(py, NESTED_ERROR)]).unwrap(),
            );
            return Err(SerializationError::Dict(err_dict.unbind()));
        }

        if self.can_use_direct_slots && self.pre_loads.is_empty() {
            self.load_from_json_bytes_direct_slots(py, registry, bytes, pos)
        } else {
            self.load_from_json_bytes_kwargs(py, registry, bytes, pos)
        }
    }

    fn load_from_json_bytes_kwargs(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        bytes: &[u8],
        pos: &mut usize,
    ) -> Result<Py<PyAny>, SerializationError> {
        let kwargs = PyDict::new(py);
        let mut seen = SmallBitVec::from_elem(self.fields.len(), false);
        let mut errors: Option<Bound<'_, PyDict>> = None;

        if peek_char(bytes, pos) != Some(b'}') {
            loop {
                let key = read_json_string(bytes, pos)
                    .ok_or_else(|| SerializationError::simple(py, "Expected string key"))?;
                if !expect_char(bytes, pos, b':') {
                    return Err(SerializationError::simple(py, "Expected ':'"));
                }

                if let Some(&idx) = self.field_lookup.get(key.as_ref()) {
                    let dc_field = &self.fields[idx];
                    let common = dc_field.field.common();
                    seen.set(idx, true);

                    if dc_field.field_init {
                        match dc_field
                            .field
                            .load_from_json_bytes(py, registry, bytes, pos)
                        {
                            Ok(py_val) => {
                                match apply_validate(py, py_val, common.validator.as_ref()) {
                                    Ok(validated) => {
                                        let _ = kwargs
                                            .set_item(dc_field.name_interned.bind(py), validated);
                                    }
                                    Err(ref e) => {
                                        accumulate_error(
                                            py,
                                            &mut errors,
                                            dc_field.name_interned.bind(py),
                                            e,
                                        );
                                    }
                                }
                            }
                            Err(ref e) => {
                                accumulate_error(
                                    py,
                                    &mut errors,
                                    dc_field.name_interned.bind(py),
                                    e,
                                );
                            }
                        }
                    } else {
                        skip_json_value(bytes, pos);
                    }
                } else {
                    skip_json_value(bytes, pos);
                }

                if !expect_char(bytes, pos, b',') {
                    break;
                }
            }
        }
        expect_char(bytes, pos, b'}');

        for (idx, dc_field) in self.fields.iter().enumerate() {
            let common = dc_field.field.common();
            if errors
                .as_ref()
                .is_some_and(|e| e.contains(dc_field.name_interned.bind(py)).unwrap_or(false))
            {
                continue;
            }
            if !seen[idx] && dc_field.field_init {
                match get_default_value(py, common) {
                    Ok(Some(val)) => {
                        let _ = kwargs.set_item(dc_field.name_interned.bind(py), val);
                    }
                    Ok(None) => {
                        let err_list = common.required_error.as_ref().map_or_else(
                            || {
                                PyList::new(py, [intern!(py, "Missing data for required field.")])
                                    .unwrap()
                            },
                            |s| PyList::new(py, [s.bind(py)]).unwrap(),
                        );
                        let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                        let _ = err_dict.set_item(dc_field.name_interned.bind(py), err_list);
                    }
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                    }
                }
            }
        }

        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }

        self.cls
            .bind(py)
            .call((), Some(&kwargs))
            .map(Bound::unbind)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))
    }

    fn load_from_json_bytes_direct_slots(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        bytes: &[u8],
        pos: &mut usize,
    ) -> Result<Py<PyAny>, SerializationError> {
        let object_type =
            get_object_cls(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let instance = object_type
            .call_method1(intern!(py, "__new__"), (self.cls.bind(py),))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        let mut field_values: Vec<Option<Py<PyAny>>> =
            (0..self.fields.len()).map(|_| None).collect();
        let mut errors: Option<Bound<'_, PyDict>> = None;

        if peek_char(bytes, pos) != Some(b'}') {
            loop {
                let key = read_json_string(bytes, pos)
                    .ok_or_else(|| SerializationError::simple(py, "Expected string key"))?;
                if !expect_char(bytes, pos, b':') {
                    return Err(SerializationError::simple(py, "Expected ':'"));
                }

                if let Some(&idx) = self.field_lookup.get(key.as_ref()) {
                    let dc_field = &self.fields[idx];
                    let common = dc_field.field.common();

                    match dc_field
                        .field
                        .load_from_json_bytes(py, registry, bytes, pos)
                    {
                        Ok(py_val) => match apply_validate(py, py_val, common.validator.as_ref()) {
                            Ok(validated) => {
                                field_values[idx] = Some(validated);
                            }
                            Err(ref e) => {
                                accumulate_error(
                                    py,
                                    &mut errors,
                                    dc_field.name_interned.bind(py),
                                    e,
                                );
                            }
                        },
                        Err(ref e) => {
                            accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        }
                    }
                } else {
                    skip_json_value(bytes, pos);
                }

                if !expect_char(bytes, pos, b',') {
                    break;
                }
            }
        }
        expect_char(bytes, pos, b'}');

        for (idx, dc_field) in self.fields.iter().enumerate() {
            let common = dc_field.field.common();
            if errors
                .as_ref()
                .is_some_and(|e| e.contains(dc_field.name_interned.bind(py)).unwrap_or(false))
            {
                continue;
            }
            let py_value = if let Some(value) = field_values[idx].take() {
                value
            } else {
                match get_default_value(py, common) {
                    Ok(Some(val)) => val,
                    Ok(None) => {
                        let err_list = common.required_error.as_ref().map_or_else(
                            || {
                                PyList::new(py, [intern!(py, "Missing data for required field.")])
                                    .unwrap()
                            },
                            |s| PyList::new(py, [s.bind(py)]).unwrap(),
                        );
                        let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                        let _ = err_dict.set_item(dc_field.name_interned.bind(py), err_list);
                        continue;
                    }
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        continue;
                    }
                }
            };

            if let Some(offset) = dc_field.slot_offset {
                if !unsafe { set_slot_value_direct(&instance, offset, py_value) } {
                    let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
                    let _ = err_dict.set_item(
                        dc_field.name_interned.bind(py),
                        PyList::new(
                            py,
                            [intern!(py, "Failed to set slot value: null object pointer")],
                        )
                        .unwrap(),
                    );
                }
            } else {
                instance
                    .setattr(dc_field.name_interned.bind(py), py_value)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            }
        }

        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }

        Ok(instance.unbind())
    }
}

impl TypeContainer {
    pub fn load_from_json_bytes(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        bytes: &[u8],
        pos: &mut usize,
    ) -> Result<Py<PyAny>, SerializationError> {
        match self {
            Self::Dataclass(idx) => registry
                .get(*idx)
                .load_from_json_bytes(py, registry, bytes, pos),
            Self::Primitive(p) => {
                skip_whitespace(bytes, pos);
                if bytes[*pos..].starts_with(b"null") {
                    *pos += 4;
                    return Ok(py.None());
                }
                p.field.load_from_json_bytes(py, registry, bytes, pos)
            }
            Self::List { item } => {
                if !expect_char(bytes, pos, b'[') {
                    return Err(SerializationError::Single(
                        intern!(py, "Expected a list").clone().unbind(),
                    ));
                }
                let mut items = Vec::new();
                let mut errors: Option<Bound<'_, PyDict>> = None;
                if peek_char(bytes, pos) != Some(b']') {
                    let mut idx = 0;
                    loop {
                        match item.load_from_json_bytes(py, registry, bytes, pos) {
                            Ok(py_val) => items.push(py_val),
                            Err(ref e) => accumulate_error(py, &mut errors, idx, e),
                        }
                        idx += 1;
                        if !expect_char(bytes, pos, b',') {
                            break;
                        }
                    }
                }
                if !expect_char(bytes, pos, b']') {
                    return Err(SerializationError::simple(py, "Expected ']'"));
                }
                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }
                let result = new_presized_list(py, items.len());
                for (idx, item) in items.into_iter().enumerate() {
                    unsafe {
                        pyo3::ffi::PyList_SET_ITEM(
                            result.as_ptr(),
                            idx.cast_signed(),
                            item.into_ptr(),
                        );
                    }
                }
                Ok(result.into_any().unbind())
            }
            Self::Dict {
                value: value_container,
            } => {
                if !expect_char(bytes, pos, b'{') {
                    return Err(SerializationError::Single(
                        intern!(py, "Expected a dict").clone().unbind(),
                    ));
                }
                let result = PyDict::new(py);
                let mut errors: Option<Bound<'_, PyDict>> = None;
                if peek_char(bytes, pos) != Some(b'}') {
                    loop {
                        let key = read_json_string(bytes, pos)
                            .ok_or_else(|| SerializationError::simple(py, "Expected string key"))?;
                        if !expect_char(bytes, pos, b':') {
                            return Err(SerializationError::simple(py, "Expected ':'"));
                        }
                        match value_container.load_from_json_bytes(py, registry, bytes, pos) {
                            Ok(py_val) => {
                                let _ = result.set_item(&*key, py_val);
                            }
                            Err(ref e) => accumulate_error(py, &mut errors, key.as_ref(), e),
                        }
                        if !expect_char(bytes, pos, b',') {
                            break;
                        }
                    }
                }
                if !expect_char(bytes, pos, b'}') {
                    return Err(SerializationError::simple(py, "Expected '}'"));
                }
                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }
                Ok(result.into_any().unbind())
            }
            Self::Optional { inner } => {
                skip_whitespace(bytes, pos);
                if bytes[*pos..].starts_with(b"null") {
                    *pos += 4;
                    Ok(py.None())
                } else {
                    inner.load_from_json_bytes(py, registry, bytes, pos)
                }
            }
            Self::Set { item } | Self::FrozenSet { item } | Self::Tuple { item } => {
                if !expect_char(bytes, pos, b'[') {
                    let err = match self {
                        Self::Set { .. } => intern!(py, "Not a valid set."),
                        Self::FrozenSet { .. } => intern!(py, "Not a valid frozenset."),
                        _ => intern!(py, "Not a valid tuple."),
                    };
                    return Err(SerializationError::Single(err.clone().unbind()));
                }
                let mut items = Vec::new();
                let mut errors: Option<Bound<'_, PyDict>> = None;
                if peek_char(bytes, pos) != Some(b']') {
                    let mut idx = 0;
                    loop {
                        match item.load_from_json_bytes(py, registry, bytes, pos) {
                            Ok(py_val) => items.push(py_val),
                            Err(ref e) => accumulate_error(py, &mut errors, idx, e),
                        }
                        idx += 1;
                        if !expect_char(bytes, pos, b',') {
                            break;
                        }
                    }
                }
                expect_char(bytes, pos, b']');
                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }
                match self {
                    Self::Set { .. } => PySet::new(py, &items)
                        .map(|s| s.into_any().unbind())
                        .map_err(|e| SerializationError::simple(py, &e.to_string())),
                    Self::FrozenSet { .. } => PyFrozenSet::new(py, &items)
                        .map(|s| s.into_any().unbind())
                        .map_err(|e| SerializationError::simple(py, &e.to_string())),
                    _ => PyTuple::new(py, &items)
                        .map(|t| t.into_any().unbind())
                        .map_err(|e| SerializationError::simple(py, &e.to_string())),
                }
            }
            Self::Union { variants } => {
                let checkpoint = *pos;
                let mut errors = Vec::new();
                for variant in variants {
                    *pos = checkpoint;
                    match variant.load_from_json_bytes(py, registry, bytes, pos) {
                        Ok(result) => return Ok(result),
                        Err(e) => errors.push(e),
                    }
                }
                Err(SerializationError::collect_list(py, errors))
            }
        }
    }
}

fn parse_any_json_value(
    py: Python<'_>,
    bytes: &[u8],
    pos: &mut usize,
) -> Result<Py<PyAny>, SerializationError> {
    skip_whitespace(bytes, pos);
    if *pos >= bytes.len() {
        return Err(SerializationError::simple(py, "Unexpected end of JSON"));
    }
    match bytes[*pos] {
        b'"' => {
            let s = read_json_string(bytes, pos)
                .ok_or_else(|| SerializationError::simple(py, "Invalid string"))?;
            Ok(PyString::new(py, &s).into_any().unbind())
        }
        b'{' => {
            *pos += 1;
            let result = PyDict::new(py);
            if peek_char(bytes, pos) != Some(b'}') {
                loop {
                    let key = read_json_string(bytes, pos)
                        .ok_or_else(|| SerializationError::simple(py, "Expected key"))?;
                    if !expect_char(bytes, pos, b':') {
                        return Err(SerializationError::simple(py, "Expected ':'"));
                    }
                    let val = parse_any_json_value(py, bytes, pos)?;
                    let _ = result.set_item(&*key, val);
                    if !expect_char(bytes, pos, b',') {
                        break;
                    }
                }
            }
            expect_char(bytes, pos, b'}');
            Ok(result.into_any().unbind())
        }
        b'[' => {
            *pos += 1;
            let mut items = Vec::new();
            if peek_char(bytes, pos) != Some(b']') {
                loop {
                    items.push(parse_any_json_value(py, bytes, pos)?);
                    if !expect_char(bytes, pos, b',') {
                        break;
                    }
                }
            }
            expect_char(bytes, pos, b']');
            PyList::new(py, items)
                .map(|l| l.into_any().unbind())
                .map_err(|e| SerializationError::simple(py, &e.to_string()))
        }
        b't' => {
            if bytes[*pos..].starts_with(b"true") {
                *pos += 4;
                Ok(PyBool::new(py, true).to_owned().into_any().unbind())
            } else {
                Err(SerializationError::simple(py, "Invalid JSON"))
            }
        }
        b'f' => {
            if bytes[*pos..].starts_with(b"false") {
                *pos += 5;
                Ok(PyBool::new(py, false).to_owned().into_any().unbind())
            } else {
                Err(SerializationError::simple(py, "Invalid JSON"))
            }
        }
        b'n' => {
            if bytes[*pos..].starts_with(b"null") {
                *pos += 4;
                Ok(py.None())
            } else {
                Err(SerializationError::simple(py, "Invalid JSON"))
            }
        }
        b'0'..=b'9' | b'-' => {
            let num_str = read_json_number(bytes, pos)
                .ok_or_else(|| SerializationError::simple(py, "Invalid number"))?;
            if num_str.contains('.') || num_str.contains('e') || num_str.contains('E') {
                let f: f64 = num_str
                    .parse()
                    .map_err(|_| SerializationError::simple(py, "Invalid float"))?;
                f.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            } else {
                let i: i64 = num_str
                    .parse()
                    .map_err(|_| SerializationError::simple(py, "Invalid int"))?;
                i.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            }
        }
        _ => Err(SerializationError::simple(py, "Invalid JSON")),
    }
}
