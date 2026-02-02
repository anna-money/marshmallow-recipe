#![allow(clippy::single_match_else)]
#![allow(clippy::match_same_arms)]

use std::collections::HashMap;
use std::fmt;

use chrono::{DateTime, FixedOffset, NaiveDate, NaiveTime};
use pyo3::conversion::IntoPyObjectExt;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList, PySet, PyTuple};
use rust_decimal::Decimal;
use rust_decimal::prelude::FromStr;
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde_json::Value;
use smallbitvec::SmallBitVec;

use crate::cache::get_cached_types;
use crate::load::{LoadContext, load_root_type};
use crate::loader::Loader;
use crate::fields::collection::CollectionKind;
use crate::fields::datetime::DateTimeFormat;
use crate::fields::helpers::{err_json, BOOL_ERROR, DATETIME_ERROR, DATE_ERROR, DECIMAL_NUMBER_ERROR, FLOAT_ERROR, FLOAT_NAN_ERROR, INT_ERROR, TIME_ERROR, UUID_ERROR};
use crate::fields::nested::FieldLoader;
use crate::fields::decimal::{format_decimal, DecimalBuf};
use crate::fields::{int, float, bool_type, decimal, date, time, datetime, uuid, str_type, str_enum, int_enum};
use crate::slots::set_slot_value_direct;
use crate::types::{TypeDescriptor, TypeKind};
use crate::utils::{
    call_validator, parse_datetime_with_format, pyany_to_json_value, strip_serde_locations,
    try_wrap_err_json, wrap_err_dict,
};

pub struct BytesLoadContext<'py> {
    pub py: Python<'py>,
    pub decimal_places: Option<i32>,
}

fn is_json_float_string(s: &str) -> bool {
    s.contains('.') || s.contains('e') || s.contains('E')
}

pub fn json_value_to_py(py: Python, value: &serde_json::Value) -> PyResult<Py<PyAny>> {
    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => Ok(b.into_pyobject(py)?.to_owned().into_any().unbind()),
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
                cached.int_cls.bind(py).call1((&s,)).map(pyo3::Bound::unbind)
            }
        }
        serde_json::Value::String(s) => Ok(s.as_str().into_pyobject(py)?.into_any().unbind()),
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
                let key: Py<PyAny> = if !k.is_empty() && k.chars().all(|c| c.is_ascii_digit()) {
                    k.parse::<i64>()
                        .map_err(|_| pyo3::exceptions::PyValueError::new_err(format!("Index {k} is too large")))?
                        .into_pyobject(py)?.into_any().unbind()
                } else {
                    k.as_str().into_pyobject(py)?.into_any().unbind()
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
        serde_json::Value::String(s) => Ok(s.as_str().into_pyobject(py)?.into_any().unbind()),
        _ => json_value_to_py(py, value),
    }
}

pub struct TypeDescriptorSeed<'a, 'py> {
    pub ctx: &'a BytesLoadContext<'py>,
    pub descriptor: &'a TypeDescriptor,
}

impl<'de> DeserializeSeed<'de> for TypeDescriptorSeed<'_, '_> {
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
                let loader_fields = self.descriptor.loader_fields.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing loader_fields for dataclass")
                })?;
                if self.descriptor.can_use_direct_slots {
                    deserializer.deserialize_map(DataclassDirectSlotsVisitor {
                        ctx: self.ctx,
                        cls: cls.bind(self.ctx.py),
                        fields: loader_fields,
                        field_lookup: &self.descriptor.field_lookup,
                    })
                } else {
                    deserializer.deserialize_map(DataclassVisitor {
                        ctx: self.ctx,
                        cls: cls.bind(self.ctx.py),
                        fields: loader_fields,
                        field_lookup: &self.descriptor.field_lookup,
                    })
                }
            }
            TypeKind::Primitive => {
                let prim_deserializer = self.descriptor.primitive_loader.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing primitive_loader")
                })?;
                PrimitiveLoaderSeed {
                    ctx: self.ctx,
                    deserializer: prim_deserializer,
                }.deserialize(deserializer)
            }
            TypeKind::List | TypeKind::Set | TypeKind::FrozenSet | TypeKind::Tuple => {
                let kind = match self.descriptor.type_kind {
                    TypeKind::List => CollectionKind::List,
                    TypeKind::Set => CollectionKind::Set,
                    TypeKind::FrozenSet => CollectionKind::FrozenSet,
                    TypeKind::Tuple => CollectionKind::Tuple,
                    _ => unreachable!(),
                };
                let item_descriptor = self.descriptor.item_type.as_ref().ok_or_else(|| {
                    de::Error::custom(format!("Missing item_type for {kind:?}"))
                })?;
                deserializer.deserialize_seq(TopLevelCollectionVisitor {
                    ctx: self.ctx,
                    item_descriptor,
                    kind,
                })
            }
            TypeKind::Dict => {
                let value_descriptor = self.descriptor.value_type.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing value_type for dict")
                })?;
                deserializer.deserialize_map(TopLevelDictVisitor {
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
            TypeKind::Union => {
                let variants = self.descriptor.union_variants.as_ref().ok_or_else(|| {
                    de::Error::custom("Missing union_variants for union")
                })?;
                let value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
                let py_value = json_value_to_py(self.ctx.py, &value).map_err(de::Error::custom)?;
                let dict_ctx = LoadContext::new(self.ctx.py, self.ctx.decimal_places);
                for variant in variants {
                    if let Ok(result) = load_root_type(py_value.bind(self.ctx.py), variant, &dict_ctx) {
                        return Ok(result);
                    }
                }
                Err(de::Error::custom("Value does not match any union variant"))
            }
        }
    }
}

struct TopLevelCollectionVisitor<'a, 'py> {
    ctx: &'a BytesLoadContext<'py>,
    item_descriptor: &'a TypeDescriptor,
    kind: CollectionKind,
}

impl<'de> Visitor<'de> for TopLevelCollectionVisitor<'_, '_> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        let name = match self.kind {
            CollectionKind::List => "a JSON array",
            CollectionKind::Set => "a JSON array for set",
            CollectionKind::FrozenSet => "a JSON array for frozenset",
            CollectionKind::Tuple => "a JSON array for tuple",
        };
        formatter.write_str(name)
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
        match self.kind {
            CollectionKind::List => Ok(PyList::new(py, items).map_err(de::Error::custom)?.unbind().into()),
            CollectionKind::Set => Ok(PySet::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
            CollectionKind::FrozenSet => Ok(PyFrozenSet::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
            CollectionKind::Tuple => Ok(PyTuple::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
        }
    }
}

struct TopLevelDictVisitor<'a, 'py> {
    ctx: &'a BytesLoadContext<'py>,
    value_descriptor: &'a TypeDescriptor,
}

impl<'de> Visitor<'de> for TopLevelDictVisitor<'_, '_> {
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

struct OptionalVisitor<'a, 'py> {
    ctx: &'a BytesLoadContext<'py>,
    inner_descriptor: Option<&'a TypeDescriptor>,
}

impl<'de> Visitor<'de> for OptionalVisitor<'_, '_> {
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
        self.inner_descriptor.map_or_else(
            || Err(de::Error::custom("Missing inner_type for optional")),
            |inner| TypeDescriptorSeed { ctx: self.ctx, descriptor: inner }.deserialize(deserializer),
        )
    }
}

pub struct FieldLoaderSeed<'a, 'py> {
    pub ctx: &'a BytesLoadContext<'py>,
    pub field: &'a FieldLoader,
}

impl<'de> DeserializeSeed<'de> for FieldLoaderSeed<'_, '_> {
    type Value = Py<PyAny>;

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: de::Deserializer<'de>,
    {
        if matches!(self.field.loader, Loader::Any) {
            let json_value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
            return json_value_to_py(self.ctx.py, &json_value).map_err(de::Error::custom);
        }
        if matches!(self.field.loader, Loader::Union { .. }) {
            let json_value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
            let py_value = json_value_to_py(self.ctx.py, &json_value).map_err(de::Error::custom)?;
            let dict_ctx = crate::types::LoadContext::new(self.ctx.py, self.ctx.decimal_places);
            return self.field.loader.load_from_dict(
                py_value.bind(self.ctx.py),
                &self.field.name,
                self.field.invalid_error.as_deref(),
                &dict_ctx,
            ).map_err(|e| de::Error::custom(e.to_string()));
        }
        deserializer.deserialize_any(FieldValueVisitor {
            ctx: self.ctx,
            field: self.field,
        })
    }
}

struct FieldValueVisitor<'a, 'py> {
    ctx: &'a BytesLoadContext<'py>,
    field: &'a FieldLoader,
}

impl<'de> Visitor<'de> for FieldValueVisitor<'_, '_> {
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
        match &self.field.loader {
            Loader::Bool => v.into_py_any(self.ctx.py).map_err(de::Error::custom),
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_i64<E>(self, v: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.field.loader {
            Loader::Int => v.into_py_any(self.ctx.py).map_err(de::Error::custom),
            Loader::Float => v.into_py_any(self.ctx.py).map_err(de::Error::custom),
            Loader::Bool => {
                match v {
                    0 => false.into_py_any(self.ctx.py).map_err(de::Error::custom),
                    1 => true.into_py_any(self.ctx.py).map_err(de::Error::custom),
                    _ => {
                        let msg = self.field.invalid_error.as_deref().unwrap_or(BOOL_ERROR);
                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                    }
                }
            }
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_i64(
                    self.ctx.py, v, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, self.field.invalid_error.as_deref().unwrap_or(DECIMAL_NUMBER_ERROR),
                ).map_err(|e: de::value::Error| de::Error::custom(err_json(&self.field.name, &e.to_string())))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                let err_msg = err_json(&self.field.name, self.field.invalid_error.as_deref().unwrap_or(DATETIME_ERROR));
                #[allow(clippy::cast_precision_loss)]
                datetime::datetime_loader::load_from_timestamp(self.ctx.py, v as f64, &err_msg)
            }
            Loader::IntEnum(data) => {
                for (k, member) in &data.values {
                    if *k == v {
                        return Ok(member.clone_ref(self.ctx.py));
                    }
                }
                let msg = crate::fields::int_enum::int_enum_loader::format_visit_error(v, &data.values, self.field.invalid_error.as_deref());
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            Loader::StrEnum(data) => {
                let msg = crate::fields::str_enum::str_enum_loader::format_visit_error(v, &data.values, self.field.invalid_error.as_deref());
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_u64<E>(self, v: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.field.loader {
            Loader::Int => v.into_py_any(self.ctx.py).map_err(de::Error::custom),
            Loader::Float => v.into_py_any(self.ctx.py).map_err(de::Error::custom),
            Loader::Bool => {
                match v {
                    0 => false.into_py_any(self.ctx.py).map_err(de::Error::custom),
                    1 => true.into_py_any(self.ctx.py).map_err(de::Error::custom),
                    _ => {
                        let msg = self.field.invalid_error.as_deref().unwrap_or(BOOL_ERROR);
                        Err(de::Error::custom(err_json(&self.field.name, msg)))
                    }
                }
            }
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_u64(
                    self.ctx.py, v, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, self.field.invalid_error.as_deref().unwrap_or(DECIMAL_NUMBER_ERROR),
                ).map_err(|e: de::value::Error| de::Error::custom(err_json(&self.field.name, &e.to_string())))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                let err_msg = err_json(&self.field.name, self.field.invalid_error.as_deref().unwrap_or(DATETIME_ERROR));
                #[allow(clippy::cast_precision_loss)]
                datetime::datetime_loader::load_from_timestamp(self.ctx.py, v as f64, &err_msg)
            }
            Loader::IntEnum(data) => {
                if let Ok(v_i64) = i64::try_from(v) {
                    for (k, member) in &data.values {
                        if *k == v_i64 {
                            return Ok(member.clone_ref(self.ctx.py));
                        }
                    }
                }
                let msg = crate::fields::int_enum::int_enum_loader::format_visit_error(v, &data.values, self.field.invalid_error.as_deref());
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            Loader::StrEnum(data) => {
                let msg = crate::fields::str_enum::str_enum_loader::format_visit_error(v, &data.values, self.field.invalid_error.as_deref());
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_f64<E>(self, v: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.field.loader {
            Loader::Float => v.into_py_any(self.ctx.py).map_err(de::Error::custom),
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_f64(
                    self.ctx.py, v, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, self.field.invalid_error.as_deref().unwrap_or(DECIMAL_NUMBER_ERROR),
                ).map_err(|e: de::value::Error| de::Error::custom(err_json(&self.field.name, &e.to_string())))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                let err_msg = err_json(&self.field.name, self.field.invalid_error.as_deref().unwrap_or(DATETIME_ERROR));
                datetime::datetime_loader::load_from_timestamp(self.ctx.py, v, &err_msg)
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    #[allow(clippy::too_many_lines)]
    fn visit_str<E>(self, v: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.field.loader {
            Loader::Str { strip_whitespaces } => {
                let s = if *strip_whitespaces { v.trim() } else { v };
                s.into_py_any(self.ctx.py).map_err(de::Error::custom)
            }
            Loader::Int => {
                let err_msg = || self.field.invalid_error.as_deref().unwrap_or(INT_ERROR).to_string();
                v.parse::<i64>()
                    .map_err(|_| de::Error::custom(err_json(&self.field.name, &err_msg())))
                    .and_then(|i| i.into_py_any(self.ctx.py).map_err(de::Error::custom))
            }
            Loader::Float => {
                let err_msg = || self.field.invalid_error.as_deref().unwrap_or(FLOAT_ERROR).to_string();
                let nan_err = || self.field.invalid_error.as_deref().unwrap_or(FLOAT_NAN_ERROR).to_string();
                let f: f64 = v.parse().map_err(|_| de::Error::custom(err_json(&self.field.name, &err_msg())))?;
                if f.is_nan() || f.is_infinite() {
                    return Err(de::Error::custom(err_json(&self.field.name, &nan_err())));
                }
                f.into_py_any(self.ctx.py).map_err(de::Error::custom)
            }
            Loader::Decimal(data) => {
                let err_msg = || self.field.invalid_error.as_deref().unwrap_or(DECIMAL_NUMBER_ERROR).to_string();
                let rust_decimal = Decimal::from_str(v)
                    .or_else(|_| Decimal::from_scientific(v))
                    .map_err(|_| de::Error::custom(err_json(&self.field.name, &err_msg())))?;

                let places = data.decimal_places.resolve(self.ctx.decimal_places);
                let final_decimal = if let Some(places) = places {
                    if let Some(strategy) = data.rounding_strategy {
                        rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy)
                    } else {
                        let normalized = rust_decimal.normalize();
                        if normalized.scale() > places.cast_unsigned() {
                            return Err(de::Error::custom(err_json(&self.field.name, &err_msg())));
                        }
                        rust_decimal
                    }
                } else {
                    rust_decimal
                };

                let mut buf = DecimalBuf::new();
                format_decimal(&mut buf, &final_decimal);
                let cached = get_cached_types(self.ctx.py).map_err(de::Error::custom)?;
                cached.decimal_cls.bind(self.ctx.py).call1((buf.as_str(),))
                    .map(Bound::unbind)
                    .map_err(de::Error::custom)
            }
            Loader::Date => {
                let err_msg = || self.field.invalid_error.as_deref().unwrap_or(DATE_ERROR).to_string();
                v.parse::<NaiveDate>()
                    .map_err(|_| de::Error::custom(err_json(&self.field.name, &err_msg())))
                    .and_then(|d| d.into_py_any(self.ctx.py).map_err(de::Error::custom))
            }
            Loader::Time => {
                let err_msg = || self.field.invalid_error.as_deref().unwrap_or(TIME_ERROR).to_string();
                v.parse::<NaiveTime>()
                    .map_err(|_| de::Error::custom(err_json(&self.field.name, &err_msg())))
                    .and_then(|t| t.into_py_any(self.ctx.py).map_err(de::Error::custom))
            }
            Loader::DateTime { format } => {
                let err_msg = || self.field.invalid_error.as_deref().unwrap_or(DATETIME_ERROR).to_string();
                match format {
                    DateTimeFormat::Iso => {
                        DateTime::<FixedOffset>::parse_from_rfc3339(v)
                            .map_err(|_| de::Error::custom(err_json(&self.field.name, &err_msg())))
                            .and_then(|dt| dt.into_py_any(self.ctx.py).map_err(de::Error::custom))
                    }
                    DateTimeFormat::Timestamp => {
                        Err(de::Error::custom(err_json(&self.field.name, &err_msg())))
                    }
                    DateTimeFormat::Strftime(chrono_fmt) => {
                        if let Some(dt) = parse_datetime_with_format(v, chrono_fmt) {
                            return dt.into_py_any(self.ctx.py).map_err(de::Error::custom);
                        }
                        Err(de::Error::custom(err_json(&self.field.name, &err_msg())))
                    }
                }
            }
            Loader::Uuid => {
                let err_msg = || self.field.invalid_error.as_deref().unwrap_or(UUID_ERROR).to_string();
                let parsed_uuid = ::uuid::Uuid::parse_str(v).map_err(|_| de::Error::custom(err_json(&self.field.name, &err_msg())))?;
                parsed_uuid
                    .into_pyobject(self.ctx.py)
                    .map(|b| b.into_any().unbind())
                    .map_err(de::Error::custom)
            }
            Loader::StrEnum(data) => {
                for (k, member) in &data.values {
                    if k == v {
                        return Ok(member.clone_ref(self.ctx.py));
                    }
                }
                let msg = crate::fields::str_enum::str_enum_loader::format_visit_error(v, &data.values, self.field.invalid_error.as_deref());
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            Loader::IntEnum(data) => {
                let msg = crate::fields::int_enum::int_enum_loader::format_visit_error(v, &data.values, self.field.invalid_error.as_deref());
                Err(de::Error::custom(err_json(&self.field.name, &msg)))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
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
        match &self.field.loader {
            Loader::Collection(data) => {
                let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
                let mut item_errors: Vec<(usize, Py<PyAny>)> = Vec::new();
                let mut idx = 0usize;

                while let Some(item) = seq.next_element_seed(PrimitiveLoaderSeed {
                    ctx: self.ctx,
                    deserializer: &data.item,
                }).map_err(|e| {
                    try_wrap_err_json(&idx.to_string(), &e.to_string())
                        .and_then(|wrapped| try_wrap_err_json(&self.field.name, &wrapped))
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })? {
                    if let Some(ref validator) = self.field.item_validator {
                        if let Some(errors) = call_validator(self.ctx.py, validator, item.bind(self.ctx.py)).map_err(de::Error::custom)? {
                            item_errors.push((idx, errors));
                        }
                    }
                    items.push(item);
                    idx += 1;
                }

                if !item_errors.is_empty() {
                    let formatted = format_item_errors_json_from_vec(self.ctx.py, &item_errors);
                    return Err(de::Error::custom(wrap_err_json(&self.field.name, &formatted)));
                }

                let py = self.ctx.py;
                match data.kind {
                    CollectionKind::List => Ok(PyList::new(py, items).map_err(de::Error::custom)?.unbind().into()),
                    CollectionKind::Set => Ok(PySet::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
                    CollectionKind::FrozenSet => Ok(PyFrozenSet::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
                    CollectionKind::Tuple => Ok(PyTuple::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
                }
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        const SERDE_JSON_NUMBER_TOKEN: &str = "$serde_json::private::Number";

        match &self.field.loader {
            Loader::Int | Loader::Float | Loader::Decimal(_) => {
                if let Some(key) = map.next_key::<&str>()? {
                    if key == SERDE_JSON_NUMBER_TOKEN {
                        let num_str: String = map.next_value()?;
                        return self.visit_big_number(&num_str);
                    }
                }
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                if let Some(key) = map.next_key::<&str>()? {
                    if key == SERDE_JSON_NUMBER_TOKEN {
                        let num_str: String = map.next_value()?;
                        let err_msg = err_json(&self.field.name, self.field.invalid_error.as_deref().unwrap_or(DATETIME_ERROR));
                        let timestamp: f64 = num_str.parse().map_err(|_| de::Error::custom(&err_msg))?;
                        return datetime::datetime_loader::load_from_timestamp(self.ctx.py, timestamp, &err_msg);
                    }
                }
                let msg = self.field.invalid_error.as_deref().unwrap_or(DATETIME_ERROR);
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
            Loader::Dict(data) => {
                let py = self.ctx.py;
                let dict = PyDict::new(py);
                while let Some(key) = map.next_key::<&str>()? {
                    let value = map.next_value_seed(PrimitiveLoaderSeed {
                        ctx: self.ctx,
                        deserializer: &data.value,
                    }).map_err(|e| {
                        try_wrap_err_json("value", &e.to_string())
                            .and_then(|wrapped| try_wrap_err_json(key, &wrapped))
                            .and_then(|wrapped| try_wrap_err_json(&self.field.name, &wrapped))
                            .map(de::Error::custom)
                            .unwrap_or(e)
                    })?;
                    if let Some(ref validator) = self.field.value_validator {
                        if let Some(errors) = call_validator(py, validator, value.bind(py)).map_err(de::Error::custom)? {
                            let inner = wrap_err_dict(py, key, errors);
                            let outer = wrap_err_dict(py, &self.field.name, inner);
                            return Err(de::Error::custom(pyany_to_json_value(outer.bind(py)).to_string()));
                        }
                    }
                    dict.set_item(key, value).map_err(de::Error::custom)?;
                }
                Ok(dict.unbind().into())
            }
            Loader::Nested { schema } => {
                let result = if schema.can_use_direct_slots {
                    DataclassDirectSlotsVisitor {
                        ctx: self.ctx,
                        cls: schema.cls.bind(self.ctx.py),
                        fields: &schema.fields,
                        field_lookup: &schema.field_lookup,
                    }.visit_map(map)
                } else {
                    DataclassVisitor {
                        ctx: self.ctx,
                        cls: schema.cls.bind(self.ctx.py),
                        fields: &schema.fields,
                        field_lookup: &schema.field_lookup,
                    }.visit_map(map)
                };
                result.map_err(|e| {
                    try_wrap_err_json(&self.field.name, &e.to_string())
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }
}

impl FieldValueVisitor<'_, '_> {
    fn visit_big_number<E>(&self, num_str: &str) -> Result<Py<PyAny>, E>
    where
        E: de::Error,
    {
        let is_float = is_json_float_string(num_str);

        match &self.field.loader {
            Loader::Int => {
                if is_float {
                    let msg = self.field.invalid_error.as_deref().unwrap_or(INT_ERROR);
                    return Err(de::Error::custom(err_json(&self.field.name, msg)));
                }
                let cached = get_cached_types(self.ctx.py).map_err(de::Error::custom)?;
                cached.int_cls.bind(self.ctx.py).call1((num_str,))
                    .map(pyo3::Bound::unbind)
                    .map_err(|_| {
                        let msg = self.field.invalid_error.as_deref().unwrap_or(INT_ERROR);
                        de::Error::custom(err_json(&self.field.name, msg))
                    })
            }
            Loader::Float => {
                num_str.parse::<f64>()
                    .map_err(|_| {
                        let msg = self.field.invalid_error.as_deref().unwrap_or(FLOAT_ERROR);
                        de::Error::custom(err_json(&self.field.name, msg))
                    })
                    .and_then(|f| f.into_py_any(self.ctx.py).map_err(de::Error::custom))
            }
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_str(
                    self.ctx.py, num_str, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, self.field.invalid_error.as_deref().unwrap_or(DECIMAL_NUMBER_ERROR),
                ).map_err(|e: de::value::Error| de::Error::custom(err_json(&self.field.name, &e.to_string())))
            }
            _ => {
                let msg = self.field.invalid_error.as_deref().unwrap_or_else(|| get_type_error(&self.field.loader));
                Err(de::Error::custom(err_json(&self.field.name, msg)))
            }
        }
    }
}

pub struct PrimitiveLoaderSeed<'a, 'py> {
    pub ctx: &'a BytesLoadContext<'py>,
    pub deserializer: &'a Loader,
}

impl<'de> DeserializeSeed<'de> for PrimitiveLoaderSeed<'_, '_> {
    type Value = Py<PyAny>;

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: de::Deserializer<'de>,
    {
        if matches!(self.deserializer, Loader::Any) {
            let json_value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
            return json_value_to_py(self.ctx.py, &json_value).map_err(de::Error::custom);
        }
        if matches!(self.deserializer, Loader::Union { .. }) {
            let json_value: serde_json::Value = serde::Deserialize::deserialize(deserializer)?;
            let py_value = json_value_to_py(self.ctx.py, &json_value).map_err(de::Error::custom)?;
            let dict_ctx = LoadContext::new(self.ctx.py, self.ctx.decimal_places);
            return self.deserializer.load_from_dict(
                py_value.bind(self.ctx.py),
                "",
                None,
                &dict_ctx,
            ).map_err(|e| de::Error::custom(e.to_string()));
        }
        deserializer.deserialize_any(PrimitiveValueVisitor {
            ctx: self.ctx,
            deserializer: self.deserializer,
        })
    }
}

struct PrimitiveValueVisitor<'a, 'py> {
    ctx: &'a BytesLoadContext<'py>,
    deserializer: &'a Loader,
}

impl<'de> Visitor<'de> for PrimitiveValueVisitor<'_, '_> {
    type Value = Py<PyAny>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        write!(formatter, "a value for primitive type")
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(self.ctx.py.None())
    }

    fn visit_none<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(self.ctx.py.None())
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
        match &self.deserializer {
            Loader::Bool => bool_type::bool_loader::load_from_bool(self.ctx.py, v),
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
        }
    }

    fn visit_i64<E>(self, v: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.deserializer {
            Loader::Int => int::int_loader::load_from_i64(self.ctx.py, v),
            Loader::Float => float::float_loader::load_from_i64(self.ctx.py, v),
            Loader::Bool => {
                match v {
                    0 => bool_type::bool_loader::load_from_bool(self.ctx.py, false),
                    1 => bool_type::bool_loader::load_from_bool(self.ctx.py, true),
                    _ => Err(de::Error::custom(err_json("", BOOL_ERROR))),
                }
            }
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_i64(
                    self.ctx.py, v, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, DECIMAL_NUMBER_ERROR,
                ).map_err(|e: de::value::Error| de::Error::custom(err_json("", &e.to_string())))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                #[allow(clippy::cast_precision_loss)]
                datetime::datetime_loader::load_from_timestamp(self.ctx.py, v as f64, &err_json("", DATETIME_ERROR))
            }
            Loader::IntEnum(data) => {
                int_enum::int_enum_loader::load_from_i64(self.ctx.py, v, &data.values, None)
                    .map_err(|e: de::value::Error| de::Error::custom(err_json("", &e.to_string())))
            }
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
        }
    }

    fn visit_u64<E>(self, v: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.deserializer {
            Loader::Int => int::int_loader::load_from_u64(self.ctx.py, v),
            Loader::Float => v.into_py_any(self.ctx.py).map_err(de::Error::custom),
            Loader::Bool => {
                match v {
                    0 => bool_type::bool_loader::load_from_bool(self.ctx.py, false),
                    1 => bool_type::bool_loader::load_from_bool(self.ctx.py, true),
                    _ => Err(de::Error::custom(err_json("", BOOL_ERROR))),
                }
            }
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_u64(
                    self.ctx.py, v, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, DECIMAL_NUMBER_ERROR,
                ).map_err(|e: de::value::Error| de::Error::custom(err_json("", &e.to_string())))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                #[allow(clippy::cast_precision_loss)]
                datetime::datetime_loader::load_from_timestamp(self.ctx.py, v as f64, &err_json("", DATETIME_ERROR))
            }
            Loader::IntEnum(data) => {
                int_enum::int_enum_loader::load_from_u64(self.ctx.py, v, &data.values, None)
                    .map_err(|e: de::value::Error| de::Error::custom(err_json("", &e.to_string())))
            }
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
        }
    }

    fn visit_f64<E>(self, v: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.deserializer {
            Loader::Float => float::float_loader::load_from_f64(self.ctx.py, v),
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_f64(
                    self.ctx.py, v, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, DECIMAL_NUMBER_ERROR,
                ).map_err(|e: de::value::Error| de::Error::custom(err_json("", &e.to_string())))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                datetime::datetime_loader::load_from_timestamp(self.ctx.py, v, &err_json("", DATETIME_ERROR))
            }
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
        }
    }

    fn visit_str<E>(self, v: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        match &self.deserializer {
            Loader::Str { strip_whitespaces } => {
                str_type::str_loader::load_from_str(self.ctx.py, v, *strip_whitespaces)
            }
            Loader::Int => int::int_loader::load_from_str(self.ctx.py, v, &err_json("", INT_ERROR)),
            Loader::Float => float::float_loader::load_from_str(self.ctx.py, v, &err_json("", FLOAT_ERROR), &err_json("", FLOAT_NAN_ERROR)),
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_str(
                    self.ctx.py, v, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, &err_json("", DECIMAL_NUMBER_ERROR),
                )
            }
            Loader::Date => date::date_loader::load_from_str(self.ctx.py, v, &err_json("", DATE_ERROR)),
            Loader::Time => time::time_loader::load_from_str(self.ctx.py, v, &err_json("", TIME_ERROR)),
            Loader::DateTime { format } => {
                datetime::datetime_loader::load_from_str(self.ctx.py, v, format, &err_json("", DATETIME_ERROR))
            }
            Loader::Uuid => uuid::uuid_loader::load_from_str(self.ctx.py, v, &err_json("", UUID_ERROR)),
            Loader::StrEnum(data) => {
                str_enum::str_enum_loader::load_from_str(self.ctx.py, v, &data.values, None)
                    .map_err(|e: de::value::Error| de::Error::custom(err_json("", &e.to_string())))
            }
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
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
        match &self.deserializer {
            Loader::Collection(data) => {
                let mut items = Vec::with_capacity(seq.size_hint().unwrap_or(0));
                let mut idx = 0usize;
                while let Some(item) = seq.next_element_seed(PrimitiveLoaderSeed {
                    ctx: self.ctx,
                    deserializer: &data.item,
                }).map_err(|e| {
                    try_wrap_err_json(&idx.to_string(), &e.to_string())
                        .map(de::Error::custom)
                        .unwrap_or(e)
                })? {
                    items.push(item);
                    idx += 1;
                }
                let py = self.ctx.py;
                match data.kind {
                    CollectionKind::List => Ok(PyList::new(py, items).map_err(de::Error::custom)?.unbind().into()),
                    CollectionKind::Set => Ok(PySet::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
                    CollectionKind::FrozenSet => Ok(PyFrozenSet::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
                    CollectionKind::Tuple => Ok(PyTuple::new(py, &items).map_err(de::Error::custom)?.unbind().into()),
                }
            }
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
        }
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        const SERDE_JSON_NUMBER_TOKEN: &str = "$serde_json::private::Number";

        match &self.deserializer {
            Loader::Int | Loader::Float | Loader::Decimal(_) => {
                if let Some(key) = map.next_key::<&str>()? {
                    if key == SERDE_JSON_NUMBER_TOKEN {
                        let num_str: String = map.next_value()?;
                        return self.visit_big_number(&num_str);
                    }
                }
                Err(de::Error::custom(err_json("", get_type_error(self.deserializer))))
            }
            Loader::DateTime { format: DateTimeFormat::Timestamp } => {
                if let Some(key) = map.next_key::<&str>()? {
                    if key == SERDE_JSON_NUMBER_TOKEN {
                        let num_str: String = map.next_value()?;
                        let err_msg = err_json("", DATETIME_ERROR);
                        let timestamp: f64 = num_str.parse().map_err(|_| de::Error::custom(&err_msg))?;
                        return datetime::datetime_loader::load_from_timestamp(self.ctx.py, timestamp, &err_msg);
                    }
                }
                Err(de::Error::custom(err_json("", DATETIME_ERROR)))
            }
            Loader::Dict(data) => {
                let py = self.ctx.py;
                let dict = PyDict::new(py);
                while let Some(key) = map.next_key::<&str>()? {
                    let value = map.next_value_seed(PrimitiveLoaderSeed {
                        ctx: self.ctx,
                        deserializer: &data.value,
                    }).map_err(|e| {
                        try_wrap_err_json("value", &e.to_string())
                            .and_then(|wrapped| try_wrap_err_json(key, &wrapped))
                            .map(de::Error::custom)
                            .unwrap_or(e)
                    })?;
                    dict.set_item(key, value).map_err(de::Error::custom)?;
                }
                Ok(dict.unbind().into())
            }
            Loader::Nested { schema } => {
                if schema.can_use_direct_slots {
                    DataclassDirectSlotsVisitor {
                        ctx: self.ctx,
                        cls: schema.cls.bind(self.ctx.py),
                        fields: &schema.fields,
                        field_lookup: &schema.field_lookup,
                    }.visit_map(map)
                } else {
                    DataclassVisitor {
                        ctx: self.ctx,
                        cls: schema.cls.bind(self.ctx.py),
                        fields: &schema.fields,
                        field_lookup: &schema.field_lookup,
                    }.visit_map(map)
                }
            }
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
        }
    }
}

impl PrimitiveValueVisitor<'_, '_> {
    fn visit_big_number<E>(&self, num_str: &str) -> Result<Py<PyAny>, E>
    where
        E: de::Error,
    {
        let is_float = is_json_float_string(num_str);

        match &self.deserializer {
            Loader::Int => {
                if is_float {
                    return Err(de::Error::custom(err_json("", INT_ERROR)));
                }
                let cached = get_cached_types(self.ctx.py).map_err(de::Error::custom)?;
                cached.int_cls.bind(self.ctx.py).call1((num_str,))
                    .map(pyo3::Bound::unbind)
                    .map_err(|_| de::Error::custom(err_json("", INT_ERROR)))
            }
            Loader::Float => {
                num_str.parse::<f64>()
                    .map_err(|_| de::Error::custom(err_json("", FLOAT_ERROR)))
                    .and_then(|f| f.into_py_any(self.ctx.py).map_err(de::Error::custom))
            }
            Loader::Decimal(data) => {
                decimal::decimal_loader::load_from_str(
                    self.ctx.py, num_str, data.decimal_places, data.rounding_strategy,
                    self.ctx.decimal_places, &err_json("", DECIMAL_NUMBER_ERROR),
                )
            }
            _ => Err(de::Error::custom(err_json("", get_type_error(self.deserializer)))),
        }
    }
}

pub struct DataclassVisitor<'a, 'py> {
    pub ctx: &'a BytesLoadContext<'py>,
    pub cls: &'a Bound<'py, PyAny>,
    pub fields: &'a [FieldLoader],
    pub field_lookup: &'a HashMap<String, usize>,
}

impl<'de> Visitor<'de> for DataclassVisitor<'_, '_> {
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
                let value = map.next_value_seed(FieldLoaderSeed {
                    ctx: self.ctx,
                    field,
                })?;
                let validated = apply_post_load_and_validate_bytes(value, field, self.ctx)?;
                kwargs.set_item(field.name_interned.bind(py), validated).map_err(de::Error::custom)?;
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

        self.cls.call((), Some(&kwargs)).map(pyo3::Bound::unbind).map_err(de::Error::custom)
    }
}

pub struct DataclassDirectSlotsVisitor<'a, 'py> {
    pub ctx: &'a BytesLoadContext<'py>,
    pub cls: &'a Bound<'py, PyAny>,
    pub fields: &'a [FieldLoader],
    pub field_lookup: &'a HashMap<String, usize>,
}

impl<'de> Visitor<'de> for DataclassDirectSlotsVisitor<'_, '_> {
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
        let instance = object_type.call_method1(intern!(py, "__new__"), (self.cls,))
            .map_err(de::Error::custom)?;

        let mut seen_fields = SmallBitVec::from_elem(self.fields.len(), false);

        while let Some(key) = map.next_key::<&str>()? {
            if let Some(&idx) = self.field_lookup.get(key) {
                let field = &self.fields[idx];
                seen_fields.set(idx, true);
                let value = map.next_value_seed(FieldLoaderSeed {
                    ctx: self.ctx,
                    field,
                })?;
                let validated = apply_post_load_and_validate_bytes(value, field, self.ctx)?;

                if let Some(offset) = field.slot_offset {
                    unsafe {
                        set_slot_value_direct(&instance, offset, validated);
                    }
                } else {
                    instance.setattr(field.name_interned.bind(py), validated).map_err(de::Error::custom)?;
                }
            } else {
                let _ = map.next_value::<serde::de::IgnoredAny>()?;
            }
        }

        for (idx, field) in self.fields.iter().enumerate() {
            if !seen_fields[idx] {
                let Some(py_value) = get_default_value_bytes(field, py)? else {
                    let msg = field.required_error.as_deref().unwrap_or("Missing data for required field.");
                    return Err(de::Error::custom(err_json(&field.name, msg)));
                };

                if let Some(offset) = field.slot_offset {
                    unsafe {
                        set_slot_value_direct(&instance, offset, py_value);
                    }
                } else {
                    instance.setattr(field.name_interned.bind(py), py_value).map_err(de::Error::custom)?;
                }
            }
        }

        Ok(instance.unbind())
    }
}

fn apply_post_load_and_validate_bytes<E: de::Error>(
    value: Py<PyAny>,
    field: &FieldLoader,
    ctx: &BytesLoadContext<'_>,
) -> Result<Py<PyAny>, E> {
    let mut result = value;

    if let Some(ref post_load_fn) = field.post_load {
        result = post_load_fn.call1(ctx.py, (result,)).map_err(de::Error::custom)?;
    }

    if let Some(ref validator) = field.validator {
        if let Some(errors) = call_validator(ctx.py, validator, result.bind(ctx.py)).map_err(de::Error::custom)? {
            return Err(de::Error::custom(err_json_from_list(ctx.py, &field.name, &errors)));
        }
    }

    Ok(result)
}

fn get_default_value_bytes<E: de::Error>(
    field: &FieldLoader,
    py: Python<'_>,
) -> Result<Option<Py<PyAny>>, E> {
    if let Some(ref factory) = field.default_factory {
        return Ok(Some(factory.call0(py).map_err(de::Error::custom)?));
    }
    if let Some(ref value) = field.default_value {
        return Ok(Some(value.clone_ref(py)));
    }
    Ok(field.optional.then(|| py.None()))
}

fn err_json_from_list(py: Python, field_name: &str, errors: &Py<PyAny>) -> String {
    let errors_json = pyany_to_json_value(errors.bind(py));
    if field_name.is_empty() {
        errors_json.to_string()
    } else {
        let mut map = serde_json::Map::new();
        map.insert(field_name.to_string(), errors_json);
        serde_json::Value::Object(map).to_string()
    }
}

fn wrap_err_json(field_name: &str, inner: &str) -> String {
    try_wrap_err_json(field_name, inner).unwrap_or_else(|| inner.to_string())
}

fn format_item_errors_json_from_vec(py: Python, errors: &[(usize, Py<PyAny>)]) -> String {
    let mut map = serde_json::Map::with_capacity(errors.len());
    for (idx, err_list) in errors {
        map.insert(idx.to_string(), pyany_to_json_value(err_list.bind(py)));
    }
    serde_json::Value::Object(map).to_string()
}

fn get_type_error(deserializer: &Loader) -> &'static str {
    use crate::fields::helpers::{BOOL_ERROR, DICT_ERROR, NESTED_ERROR, STR_ERROR, UNION_ERROR};
    match deserializer {
        Loader::Str { .. } => STR_ERROR,
        Loader::Int => INT_ERROR,
        Loader::Float => FLOAT_ERROR,
        Loader::Bool => BOOL_ERROR,
        Loader::Decimal(_) => DECIMAL_NUMBER_ERROR,
        Loader::Date => DATE_ERROR,
        Loader::Time => TIME_ERROR,
        Loader::DateTime { .. } => DATETIME_ERROR,
        Loader::Uuid => UUID_ERROR,
        Loader::StrEnum(_) | Loader::IntEnum(_) => "Invalid enum value.",
        Loader::Any => "Any",
        Loader::Collection(data) => data.kind.error_msg(),
        Loader::Dict(_) => DICT_ERROR,
        Loader::Nested { .. } => NESTED_ERROR,
        Loader::Union { .. } => UNION_ERROR,
    }
}

pub fn load_from_bytes(
    py: Python<'_>,
    json_bytes: &[u8],
    descriptor: &TypeDescriptor,
    decimal_places: Option<i32>,
) -> PyResult<Py<PyAny>> {
    let ctx = BytesLoadContext { py, decimal_places };
    let mut deserializer = serde_json::Deserializer::from_slice(json_bytes);
    TypeDescriptorSeed { ctx: &ctx, descriptor }
        .deserialize(&mut deserializer)
        .map_err(|e| raw_err_to_py_err(py, &e.to_string()))
}

fn raw_err_to_py_err(py: Python, err: &str) -> PyErr {
    let msg = strip_serde_locations(err);
    let py_err = serde_json::from_str::<Value>(&msg)
        .ok()
        .and_then(|v| json_error_to_py(py, &v).ok())
        .unwrap_or_else(|| msg.clone().into_pyobject(py).unwrap().into_any().unbind());
    PyErr::new::<pyo3::exceptions::PyValueError, _>(py_err)
}
