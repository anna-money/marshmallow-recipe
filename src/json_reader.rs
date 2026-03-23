use std::collections::HashMap;

use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use chrono::{DateTime, FixedOffset, NaiveDateTime, NaiveTime};
use pyo3::conversion::IntoPyObjectExt;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDict, PyFrozenSet, PyList, PySet, PyString, PyTuple};
use serde_json::Value;
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
use crate::utils::{call_validator, get_object_cls, parse_datetime_with_format};

const NESTED_ERROR: &str = "Invalid input type.";

fn call_validator_with_error(
    validator: &Py<PyAny>,
    value: &Bound<'_, PyAny>,
) -> Result<(), SerializationError> {
    let py = value.py();
    match call_validator(py, validator, value) {
        Ok(None) => Ok(()),
        Ok(Some(errors)) => Err(crate::error::pyerrors_to_serialization_error(py, &errors)),
        Err(e) => {
            let error_value = crate::utils::extract_error_args(py, &e);
            Err(crate::error::pyerrors_to_serialization_error(
                py,
                &error_value,
            ))
        }
    }
}

fn apply_validate(
    py: Python<'_>,
    value: Py<PyAny>,
    validator: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, SerializationError> {
    if let Some(validator) = validator {
        call_validator_with_error(validator, value.bind(py))?;
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

#[allow(clippy::cast_sign_loss)]
impl FieldContainer {
    pub fn load_from_json(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        value: &Value,
    ) -> Result<Py<PyAny>, SerializationError> {
        let common = self.common();

        if value.is_null() {
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
                let s = value.as_str().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
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
                    let result: Py<PyAny> = PyString::new(py, s).into_any().unbind();
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
                if let Some(n) = value.as_i64() {
                    let result = n
                        .into_py_any(py)
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    validate_range(
                        result.bind(py),
                        gt.as_ref(),
                        gte.as_ref(),
                        lt.as_ref(),
                        lte.as_ref(),
                    )?;
                    return Ok(result);
                }
                if let Some(n) = value.as_u64() {
                    let result = n
                        .into_py_any(py)
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    validate_range(
                        result.bind(py),
                        gt.as_ref(),
                        gte.as_ref(),
                        lt.as_ref(),
                        lte.as_ref(),
                    )?;
                    return Ok(result);
                }
                if let Some(s) = value.as_str()
                    && let Ok(i) = s.parse::<i128>()
                {
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
                    return Ok(result);
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::Float {
                gt, gte, lt, lte, ..
            } => {
                let f = if let Some(f) = value.as_f64() {
                    f
                } else if let Some(s) = value.as_str() {
                    s.parse::<f64>().map_err(|_| {
                        SerializationError::Single(common.invalid_error.clone_ref(py))
                    })?
                } else {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                };
                if f.is_nan() || f.is_infinite() {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
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
                let b = value.as_bool().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                Ok(PyBool::new(py, b).to_owned().into_any().unbind())
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
                let s = if let Some(s) = value.as_str() {
                    s.to_owned()
                } else if let Some(n) = value.as_i64() {
                    n.to_string()
                } else if let Some(n) = value.as_u64() {
                    n.to_string()
                } else if let Some(f) = value.as_f64() {
                    f.to_string()
                } else {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                };
                let decimal_cls = get_decimal_cls(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                let py_decimal = decimal_cls
                    .call1((&s,))
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                let is_finite: bool = py_decimal
                    .call_method0(intern!(py, "is_finite"))
                    .and_then(|v| v.extract())
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                if !is_finite {
                    return Err(SerializationError::Single(
                        common.invalid_error.clone_ref(py),
                    ));
                }
                let result = finalize_decimal(
                    py,
                    &py_decimal,
                    *decimal_places,
                    rounding.as_ref(),
                    &common.invalid_error,
                )?;
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
                let s = value.as_str().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                let date: chrono::NaiveDate = s
                    .parse()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                date.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            }
            Self::Time { .. } => {
                let s = value.as_str().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                let time: NaiveTime = s
                    .parse()
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))?;
                time.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            }
            Self::DateTime { format, .. } => match format {
                DateTimeFormat::Iso => {
                    let s = value.as_str().ok_or_else(|| {
                        SerializationError::Single(common.invalid_error.clone_ref(py))
                    })?;
                    let dt = DateTime::<FixedOffset>::parse_from_rfc3339(s).or_else(|_| {
                        NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S")
                            .or_else(|_| NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S%.f"))
                            .map(|naive| naive.and_utc().fixed_offset())
                    });
                    dt.map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))
                        .and_then(|dt| {
                            dt.into_py_any(py)
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))
                        })
                }
                DateTimeFormat::Timestamp => {
                    let f = value.as_f64().ok_or_else(|| {
                        SerializationError::Single(common.invalid_error.clone_ref(py))
                    })?;
                    crate::fields::datetime::timestamp_to_datetime(f)
                        .ok_or_else(|| {
                            SerializationError::Single(common.invalid_error.clone_ref(py))
                        })
                        .and_then(|dt| {
                            dt.into_py_any(py)
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))
                        })
                }
                DateTimeFormat::Strftime(chrono_fmt) => {
                    let s = value.as_str().ok_or_else(|| {
                        SerializationError::Single(common.invalid_error.clone_ref(py))
                    })?;
                    parse_datetime_with_format(s, chrono_fmt)
                        .ok_or_else(|| {
                            SerializationError::Single(common.invalid_error.clone_ref(py))
                        })
                        .and_then(|dt| {
                            dt.into_py_any(py)
                                .map_err(|e| SerializationError::simple(py, &e.to_string()))
                        })
                }
            },
            Self::Uuid { .. } => {
                let s = value.as_str().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                ::uuid::Uuid::parse_str(s)
                    .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))
                    .and_then(|u| {
                        u.into_pyobject(py)
                            .map(|b| b.into_any().unbind())
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))
                    })
            }
            Self::Bytes { .. } => {
                let s = value.as_str().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                let input = s.as_bytes();
                let padding = input.iter().rev().take(2).filter(|&&b| b == b'=').count();
                let decoded_len = (input.len() / 4 * 3).saturating_sub(padding);
                PyBytes::new_with(py, decoded_len, |buf| {
                    STANDARD
                        .decode_slice(s, buf)
                        .map(|_| ())
                        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
                })
                .map(|b| b.into_any().unbind())
                .map_err(|_| SerializationError::Single(common.invalid_error.clone_ref(py)))
            }
            Self::StrEnum {
                common,
                loader_data,
                ..
            } => {
                let s = value.as_str().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                for (k, member) in &loader_data.values {
                    if k == s {
                        return Ok(member.clone_ref(py));
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::IntEnum {
                common,
                loader_data,
                ..
            } => {
                let n = value.as_i64().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                let py_n = n
                    .into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                for (k, member) in &loader_data.values {
                    if py_n.bind(py).eq(k.bind(py)).unwrap_or(false) {
                        return Ok(member.clone_ref(py));
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::StrLiteral { common, data } => {
                let s = value.as_str().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                for allowed in &data.values {
                    if allowed == s {
                        return Ok(PyString::new(py, s).into_any().unbind());
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::IntLiteral { common, data } => {
                let n = value.as_i64().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                let py_n = n
                    .into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                for allowed in &data.values {
                    if py_n.bind(py).eq(allowed.bind(py)).unwrap_or(false) {
                        return Ok(py_n);
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::BoolLiteral { common, data } => {
                let b = value.as_bool().ok_or_else(|| {
                    SerializationError::Single(common.invalid_error.clone_ref(py))
                })?;
                for &allowed in &data.values {
                    if b == allowed {
                        return Ok(PyBool::new(py, b).to_owned().into_any().unbind());
                    }
                }
                Err(SerializationError::Single(
                    common.invalid_error.clone_ref(py),
                ))
            }
            Self::Any { .. } => json_value_to_py(py, value),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => load_collection_from_json(
                py,
                registry,
                value,
                *kind,
                item,
                item_validator.as_ref(),
                &common.invalid_error,
            ),
            Self::Dict {
                value: value_schema,
                value_validator,
                ..
            } => load_dict_from_json(
                py,
                registry,
                value,
                value_schema,
                value_validator.as_ref(),
                &common.invalid_error,
            ),
            Self::Nested {
                dataclass_index, ..
            } => registry
                .get(*dataclass_index)
                .load_from_json(py, registry, value),
            Self::Union { variants, .. } => {
                let mut errors = Vec::new();
                for variant in variants {
                    match variant.load_from_json(py, registry, value) {
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
    pub fn load_from_json(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        value: &Value,
    ) -> Result<Py<PyAny>, SerializationError> {
        let obj = value.as_object().ok_or_else(|| {
            let err_dict = PyDict::new(py);
            let _ = err_dict.set_item(
                "_schema",
                PyList::new(py, [intern!(py, NESTED_ERROR)]).unwrap(),
            );
            SerializationError::Dict(err_dict.unbind())
        })?;

        let obj = apply_json_pre_loads(py, obj, &self.pre_loads)?;

        if self.can_use_direct_slots {
            self.load_from_json_direct_slots(py, registry, &obj)
        } else {
            self.load_from_json_kwargs(py, registry, &obj)
        }
    }

    fn load_from_json_kwargs(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        obj: &HashMap<String, Value>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let kwargs = PyDict::new(py);
        let mut seen = SmallBitVec::from_elem(self.fields.len(), false);
        let mut errors: Option<Bound<'_, PyDict>> = None;

        for (k, v) in obj {
            if let Some(&idx) = self.field_lookup.get(k.as_str()) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();
                seen.set(idx, true);

                if !dc_field.field_init {
                    continue;
                }

                match dc_field.field.load_from_json(py, registry, v) {
                    Ok(py_val) => match apply_validate(py, py_val, common.validator.as_ref()) {
                        Ok(validated) => {
                            let _ = kwargs.set_item(dc_field.name_interned.bind(py), validated);
                        }
                        Err(ref e) => {
                            accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        }
                    },
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                    }
                }
            }
        }

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

    fn load_from_json_direct_slots(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        obj: &HashMap<String, Value>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let object_type =
            get_object_cls(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let instance = object_type
            .call_method1(intern!(py, "__new__"), (self.cls.bind(py),))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        let mut field_values: Vec<Option<Py<PyAny>>> =
            (0..self.fields.len()).map(|_| None).collect();
        let mut errors: Option<Bound<'_, PyDict>> = None;

        for (k, v) in obj {
            if let Some(&idx) = self.field_lookup.get(k.as_str()) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();

                match dc_field.field.load_from_json(py, registry, v) {
                    Ok(py_val) => match apply_validate(py, py_val, common.validator.as_ref()) {
                        Ok(validated) => {
                            field_values[idx] = Some(validated);
                        }
                        Err(ref e) => {
                            accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        }
                    },
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                    }
                }
            }
        }

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
    pub fn load_from_json(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        value: &Value,
    ) -> Result<Py<PyAny>, SerializationError> {
        match self {
            Self::Dataclass(idx) => registry.get(*idx).load_from_json(py, registry, value),
            Self::Primitive(p) => {
                if value.is_null() {
                    return Ok(py.None());
                }
                p.field.load_from_json(py, registry, value)
            }
            Self::List { item } => {
                let arr = value.as_array().ok_or_else(|| {
                    SerializationError::Single(intern!(py, "Expected a list").clone().unbind())
                })?;
                let result = crate::utils::new_presized_list(py, arr.len());
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (idx, v) in arr.iter().enumerate() {
                    match item.load_from_json(py, registry, v) {
                        Ok(py_val) => unsafe {
                            pyo3::ffi::PyList_SET_ITEM(
                                result.as_ptr(),
                                idx.cast_signed(),
                                py_val.into_ptr(),
                            );
                        },
                        Err(ref e) => accumulate_error(py, &mut errors, idx, e),
                    }
                }

                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }

                Ok(result.into_any().unbind())
            }
            Self::Dict {
                value: value_container,
            } => {
                let obj = value.as_object().ok_or_else(|| {
                    SerializationError::Single(intern!(py, "Expected a dict").clone().unbind())
                })?;
                let result = PyDict::new(py);
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (k, v) in obj {
                    match value_container.load_from_json(py, registry, v) {
                        Ok(py_val) => {
                            let _ = result.set_item(k, py_val);
                        }
                        Err(ref e) => accumulate_error(py, &mut errors, k.as_str(), e),
                    }
                }

                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }

                Ok(result.into_any().unbind())
            }
            Self::Optional { inner } => {
                if value.is_null() {
                    Ok(py.None())
                } else {
                    inner.load_from_json(py, registry, value)
                }
            }
            Self::Set { item } | Self::FrozenSet { item } | Self::Tuple { item } => {
                let arr = value.as_array().ok_or_else(|| {
                    let err = match self {
                        Self::Set { .. } => intern!(py, "Not a valid set."),
                        Self::FrozenSet { .. } => intern!(py, "Not a valid frozenset."),
                        _ => intern!(py, "Not a valid tuple."),
                    };
                    SerializationError::Single(err.clone().unbind())
                })?;
                let mut items = Vec::with_capacity(arr.len());
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (idx, v) in arr.iter().enumerate() {
                    match item.load_from_json(py, registry, v) {
                        Ok(py_val) => items.push(py_val),
                        Err(ref e) => accumulate_error(py, &mut errors, idx, e),
                    }
                }

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
                let mut errors = Vec::new();
                for variant in variants {
                    match variant.load_from_json(py, registry, value) {
                        Ok(result) => return Ok(result),
                        Err(e) => errors.push(e),
                    }
                }
                Err(SerializationError::collect_list(py, errors))
            }
        }
    }
}

fn finalize_decimal(
    py: Python<'_>,
    py_decimal: &Bound<'_, PyAny>,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let Some(places) = decimal_places else {
        return Ok(py_decimal.clone().unbind());
    };
    if let Some(rounding) = rounding {
        let exp = get_quantize_exp(py, places.cast_unsigned())
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        py_decimal
            .call_method1(intern!(py, "quantize"), (&exp, rounding.bind(py)))
            .map(Bound::unbind)
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))
    } else {
        Ok(py_decimal.clone().unbind())
    }
}

fn json_value_to_py(py: Python<'_>, value: &Value) -> Result<Py<PyAny>, SerializationError> {
    match value {
        Value::Null => Ok(py.None()),
        Value::Bool(b) => Ok(PyBool::new(py, *b).to_owned().into_any().unbind()),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                i.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            } else if let Some(u) = n.as_u64() {
                u.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            } else if let Some(f) = n.as_f64() {
                f.into_py_any(py)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))
            } else {
                Err(SerializationError::simple(py, "Invalid number"))
            }
        }
        Value::String(s) => Ok(PyString::new(py, s).into_any().unbind()),
        Value::Array(arr) => {
            let items: Result<Vec<_>, _> = arr.iter().map(|v| json_value_to_py(py, v)).collect();
            PyList::new(py, items?)
                .map(|l| l.into_any().unbind())
                .map_err(|e| SerializationError::simple(py, &e.to_string()))
        }
        Value::Object(obj) => {
            let result = PyDict::new(py);
            for (k, v) in obj {
                let py_val = json_value_to_py(py, v)?;
                result
                    .set_item(k, py_val)
                    .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            }
            Ok(result.into_any().unbind())
        }
    }
}

fn load_collection_from_json(
    py: Python<'_>,
    registry: &DataclassRegistry,
    value: &Value,
    kind: CollectionKind,
    item: &FieldContainer,
    item_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let arr = value
        .as_array()
        .ok_or_else(|| SerializationError::Single(invalid_error.clone_ref(py)))?;
    let mut items = Vec::with_capacity(arr.len());
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (idx, v) in arr.iter().enumerate() {
        if v.is_null() {
            items.push(py.None());
            continue;
        }
        match item.load_from_json(py, registry, v) {
            Ok(py_val) => {
                if let Some(validator) = item_validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, py_val.bind(py))
                {
                    let e = crate::error::pyerrors_to_serialization_error(py, &err_list);
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

fn load_dict_from_json(
    py: Python<'_>,
    registry: &DataclassRegistry,
    value: &Value,
    value_schema: &FieldContainer,
    value_validator: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let obj = value
        .as_object()
        .ok_or_else(|| SerializationError::Single(invalid_error.clone_ref(py)))?;
    let result = PyDict::new(py);
    let mut errors: Option<Bound<'_, PyDict>> = None;

    for (k, v) in obj {
        if v.is_null() {
            let _ = result.set_item(k, py.None());
            continue;
        }
        match value_schema.load_from_json(py, registry, v) {
            Ok(py_val) => {
                if let Some(validator) = value_validator
                    && let Ok(Some(err_list)) = call_validator(py, validator, py_val.bind(py))
                {
                    let e = crate::error::pyerrors_to_serialization_error(py, &err_list);
                    accumulate_error(py, &mut errors, k.as_str(), &e);
                    continue;
                }
                let _ = result.set_item(k, py_val);
            }
            Err(e) => {
                let nested_dict = PyDict::new(py);
                let _ =
                    nested_dict.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
                let wrapped = SerializationError::Dict(nested_dict.unbind());
                accumulate_error(py, &mut errors, k.as_str(), &wrapped);
            }
        }
    }

    if let Some(errors) = errors {
        return Err(SerializationError::Dict(errors.unbind()));
    }

    Ok(result.into_any().unbind())
}

fn apply_json_pre_loads(
    py: Python<'_>,
    obj: &serde_json::Map<String, Value>,
    pre_loads: &[Py<PyAny>],
) -> Result<HashMap<String, Value>, SerializationError> {
    if pre_loads.is_empty() {
        return Ok(obj.iter().map(|(k, v)| (k.clone(), v.clone())).collect());
    }

    let py_dict = PyDict::new(py);
    for (k, v) in obj {
        let py_val = json_value_to_py(py, v)?;
        py_dict
            .set_item(k, py_val)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    }

    let mut current = py_dict;
    for hook in pre_loads {
        current = hook
            .call1(py, (&current,))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?
            .into_bound(py)
            .cast_into::<PyDict>()
            .map_err(|_| SerializationError::simple(py, "pre_load hook must return a dict"))?;
    }

    let mut result = HashMap::new();
    for (k, v) in current.iter() {
        let key: String = k
            .extract::<String>()
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let py_val = py_to_json_value(&v)?;
        result.insert(key, py_val);
    }
    Ok(result)
}

fn py_to_json_value(value: &Bound<'_, PyAny>) -> Result<Value, SerializationError> {
    let py = value.py();
    if value.is_none() {
        return Ok(Value::Null);
    }
    if value.is_instance_of::<PyBool>() {
        let b: bool = value.extract().unwrap();
        return Ok(Value::Bool(b));
    }
    if value.is_instance_of::<pyo3::types::PyInt>()
        && let Ok(i) = value.extract::<i64>()
    {
        return Ok(Value::Number(i.into()));
    }
    if value.is_instance_of::<pyo3::types::PyFloat>()
        && let Ok(f) = value.extract::<f64>()
        && let Some(n) = serde_json::Number::from_f64(f)
    {
        return Ok(Value::Number(n));
    }
    if value.is_instance_of::<PyString>() {
        let s: String = value
            .extract::<String>()
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        return Ok(Value::String(s));
    }
    if let Ok(list) = value.cast::<PyList>() {
        let items: Result<Vec<Value>, _> = list.iter().map(|v| py_to_json_value(&v)).collect();
        return Ok(Value::Array(items?));
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (k, v) in dict.iter() {
            let key: String = k
                .extract::<String>()
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            map.insert(key, py_to_json_value(&v)?);
        }
        return Ok(Value::Object(map));
    }
    let s = value
        .str()
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    let s = s
        .to_str()
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    Ok(Value::String(s.to_owned()))
}
