use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};
use serde::ser::{SerializeMap, SerializeSeq};
use serde::{Serialize, Serializer};

use crate::field_types::nested::nested_serializer::serialize_dataclass_streaming;
use crate::types::SerializeContext;
use crate::types::{TypeDescriptor, TypeKind};

pub struct RootTypeSerializer<'a, 'py> {
    pub value: &'a Bound<'py, PyAny>,
    pub descriptor: &'a TypeDescriptor,
    pub ctx: &'a SerializeContext<'a, 'py>,
}

impl Serialize for RootTypeSerializer<'_, '_> {
    #[allow(clippy::too_many_lines)]
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        match self.descriptor.type_kind {
            TypeKind::Dataclass => {
                let serializer_fields = self.descriptor.serializer_fields.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Missing serializer_fields for dataclass")
                })?;
                serialize_dataclass_streaming(self.value, serializer_fields, self.ctx, serializer)
            }
            TypeKind::Primitive => {
                if self.value.is_none() {
                    return serializer.serialize_none();
                }
                let prim_serializer = self.descriptor.primitive_serializer.as_ref().ok_or_else(|| {
                    serde::ser::Error::custom("Missing primitive_serializer")
                })?;
                prim_serializer.serialize(self.value, "", self.ctx, serializer)
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

pub fn dump_to_bytes<'py>(
    py: Python<'py>,
    value: &Bound<'py, PyAny>,
    descriptor: &TypeDescriptor,
    none_value_handling: Option<&str>,
    global_decimal_places: Option<i32>,
) -> PyResult<Vec<u8>> {
    let ctx = SerializeContext {
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
