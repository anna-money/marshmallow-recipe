use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::PyString;

use crate::fields::collection::CollectionKind;
use crate::fields::datetime::DateTimeFormat;

pub struct FieldCommon {
    pub optional: bool,
    pub default_value: Option<Py<PyAny>>,
    pub default_factory: Option<Py<PyAny>>,
    pub required_error: Option<String>,
    pub none_error: Option<String>,
    pub invalid_error: Option<String>,
    pub validator: Option<Py<PyAny>>,
}

impl Clone for FieldCommon {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            optional: self.optional,
            default_value: self.default_value.as_ref().map(|v| v.clone_ref(py)),
            default_factory: self.default_factory.as_ref().map(|f| f.clone_ref(py)),
            required_error: self.required_error.clone(),
            none_error: self.none_error.clone(),
            invalid_error: self.invalid_error.clone(),
            validator: self.validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

pub struct DataclassField {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub data_key: Option<String>,
    pub data_key_interned: Option<Py<PyString>>,
    pub slot_offset: Option<isize>,
    pub field_init: bool,
    pub field: FieldContainer,
}

impl Clone for DataclassField {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            name: self.name.clone(),
            name_interned: self.name_interned.clone_ref(py),
            data_key: self.data_key.clone(),
            data_key_interned: self.data_key_interned.as_ref().map(|v| v.clone_ref(py)),
            slot_offset: self.slot_offset,
            field_init: self.field_init,
            field: self.field.clone(),
        })
    }
}


pub struct StrEnumLoaderData {
    pub values: Vec<(String, Py<PyAny>)>,
}

impl Clone for StrEnumLoaderData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            values: self
                .values
                .iter()
                .map(|(k, v)| (k.clone(), v.clone_ref(py)))
                .collect(),
        })
    }
}

pub struct IntEnumLoaderData {
    pub values: Vec<(Py<PyAny>, Py<PyAny>)>,
}

impl Clone for IntEnumLoaderData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            values: self
                .values
                .iter()
                .map(|(k, v)| (k.clone_ref(py), v.clone_ref(py)))
                .collect(),
        })
    }
}

#[allow(clippy::struct_field_names)]
pub struct StrEnumDumperData {
    pub enum_cls: Py<PyAny>,
    pub enum_name: Option<String>,
    pub enum_members_repr: Option<String>,
}

impl Clone for StrEnumDumperData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            enum_cls: self.enum_cls.clone_ref(py),
            enum_name: self.enum_name.clone(),
            enum_members_repr: self.enum_members_repr.clone(),
        })
    }
}

#[allow(clippy::struct_field_names)]
pub struct IntEnumDumperData {
    pub enum_cls: Py<PyAny>,
    pub enum_name: Option<String>,
    pub enum_members_repr: Option<String>,
}

impl Clone for IntEnumDumperData {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            enum_cls: self.enum_cls.clone_ref(py),
            enum_name: self.enum_name.clone(),
            enum_members_repr: self.enum_members_repr.clone(),
        })
    }
}

#[allow(clippy::use_self)]
pub enum FieldContainer {
    Str {
        common: FieldCommon,
        strip_whitespaces: bool,
        post_load: Option<Py<PyAny>>,
    },
    Int {
        common: FieldCommon,
    },
    Float {
        common: FieldCommon,
    },
    Bool {
        common: FieldCommon,
    },
    Decimal {
        common: FieldCommon,
        decimal_places: Option<i32>,
        rounding: Option<Py<PyAny>>,
    },
    Date {
        common: FieldCommon,
    },
    Time {
        common: FieldCommon,
    },
    DateTime {
        common: FieldCommon,
        format: DateTimeFormat,
    },
    Uuid {
        common: FieldCommon,
    },
    StrEnum {
        common: FieldCommon,
        loader_data: Box<StrEnumLoaderData>,
        dumper_data: Box<StrEnumDumperData>,
    },
    IntEnum {
        common: FieldCommon,
        loader_data: Box<IntEnumLoaderData>,
        dumper_data: Box<IntEnumDumperData>,
    },
    Any {
        common: FieldCommon,
    },
    Collection {
        common: FieldCommon,
        kind: CollectionKind,
        item: Box<FieldContainer>,
        item_validator: Option<Py<PyAny>>,
    },
    Dict {
        common: FieldCommon,
        value: Box<FieldContainer>,
        value_validator: Option<Py<PyAny>>,
    },
    Nested {
        common: FieldCommon,
        container: Box<DataclassContainer>,
    },
    Union {
        common: FieldCommon,
        variants: Vec<FieldContainer>,
    },
}

impl Clone for FieldContainer {
    fn clone(&self) -> Self {
        Python::attach(|py| match self {
            Self::Str { common, strip_whitespaces, post_load } => Self::Str {
                common: common.clone(),
                strip_whitespaces: *strip_whitespaces,
                post_load: post_load.as_ref().map(|v| v.clone_ref(py)),
            },
            Self::Int { common } => Self::Int { common: common.clone() },
            Self::Float { common } => Self::Float { common: common.clone() },
            Self::Bool { common } => Self::Bool { common: common.clone() },
            Self::Decimal { common, decimal_places, rounding } => Self::Decimal {
                common: common.clone(),
                decimal_places: *decimal_places,
                rounding: rounding.as_ref().map(|r| r.clone_ref(py)),
            },
            Self::Date { common } => Self::Date { common: common.clone() },
            Self::Time { common } => Self::Time { common: common.clone() },
            Self::DateTime { common, format } => Self::DateTime {
                common: common.clone(),
                format: format.clone(),
            },
            Self::Uuid { common } => Self::Uuid { common: common.clone() },
            Self::StrEnum { common, loader_data, dumper_data } => Self::StrEnum {
                common: common.clone(),
                loader_data: loader_data.clone(),
                dumper_data: dumper_data.clone(),
            },
            Self::IntEnum { common, loader_data, dumper_data } => Self::IntEnum {
                common: common.clone(),
                loader_data: loader_data.clone(),
                dumper_data: dumper_data.clone(),
            },
            Self::Any { common } => Self::Any { common: common.clone() },
            Self::Collection { common, kind, item, item_validator } => Self::Collection {
                common: common.clone(),
                kind: *kind,
                item: item.clone(),
                item_validator: item_validator.as_ref().map(|v| v.clone_ref(py)),
            },
            Self::Dict { common, value, value_validator } => Self::Dict {
                common: common.clone(),
                value: value.clone(),
                value_validator: value_validator.as_ref().map(|v| v.clone_ref(py)),
            },
            Self::Nested { common, container } => Self::Nested {
                common: common.clone(),
                container: container.clone(),
            },
            Self::Union { common, variants } => Self::Union {
                common: common.clone(),
                variants: variants.clone(),
            },
        })
    }
}

#[allow(clippy::missing_const_for_fn)]
impl FieldContainer {
    #[inline]
    pub fn common(&self) -> &FieldCommon {
        match self {
            Self::Str { common, .. }
            | Self::Int { common }
            | Self::Float { common }
            | Self::Bool { common }
            | Self::Decimal { common, .. }
            | Self::Date { common }
            | Self::Time { common }
            | Self::DateTime { common, .. }
            | Self::Uuid { common }
            | Self::StrEnum { common, .. }
            | Self::IntEnum { common, .. }
            | Self::Any { common }
            | Self::Collection { common, .. }
            | Self::Dict { common, .. }
            | Self::Nested { common, .. }
            | Self::Union { common, .. } => common,
        }
    }
}

impl std::fmt::Debug for FieldContainer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Str {
                strip_whitespaces, post_load, ..
            } => f
                .debug_struct("Str")
                .field("strip_whitespaces", strip_whitespaces)
                .field("has_post_load", &post_load.is_some())
                .finish(),
            Self::Int { .. } => write!(f, "Int"),
            Self::Float { .. } => write!(f, "Float"),
            Self::Bool { .. } => write!(f, "Bool"),
            Self::Decimal { .. } => write!(f, "Decimal"),
            Self::Date { .. } => write!(f, "Date"),
            Self::Time { .. } => write!(f, "Time"),
            Self::DateTime { format, .. } => {
                f.debug_struct("DateTime").field("format", format).finish()
            }
            Self::Uuid { .. } => write!(f, "Uuid"),
            Self::StrEnum { .. } => write!(f, "StrEnum"),
            Self::IntEnum { .. } => write!(f, "IntEnum"),
            Self::Any { .. } => write!(f, "Any"),
            Self::Collection { kind, .. } => {
                f.debug_struct("Collection").field("kind", kind).finish()
            }
            Self::Dict { .. } => write!(f, "Dict"),
            Self::Nested { .. } => write!(f, "Nested"),
            Self::Union { .. } => write!(f, "Union"),
        }
    }
}

pub struct DataclassContainer {
    pub cls: Py<PyAny>,
    pub fields: Vec<DataclassField>,
    pub field_lookup: HashMap<String, usize>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
    pub ignore_none: bool,
}

impl Clone for DataclassContainer {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
            ignore_none: self.ignore_none,
        })
    }
}

impl DataclassContainer {
    pub fn new(cls: Py<PyAny>, can_use_direct_slots: bool, has_post_init: bool, ignore_none: bool) -> Self {
        Self {
            cls,
            fields: Vec::new(),
            field_lookup: HashMap::new(),
            can_use_direct_slots,
            has_post_init,
            ignore_none,
        }
    }

    pub fn add_field(&mut self, field: DataclassField) {
        let idx = self.fields.len();
        let key = field
            .data_key
            .as_ref()
            .unwrap_or(&field.name)
            .clone();
        self.field_lookup.insert(key, idx);
        self.fields.push(field);
    }
}

impl std::fmt::Debug for DataclassContainer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("DataclassContainer")
            .field("fields", &self.fields.len())
            .field("can_use_direct_slots", &self.can_use_direct_slots)
            .finish_non_exhaustive()
    }
}

pub struct PrimitiveContainer {
    pub field: FieldContainer,
}

impl Clone for PrimitiveContainer {
    fn clone(&self) -> Self {
        Self {
            field: self.field.clone(),
        }
    }
}

#[allow(clippy::use_self)]
pub enum TypeContainer {
    Dataclass(DataclassContainer),
    Primitive(PrimitiveContainer),
    List { item: Box<Self> },
    Dict { value: Box<Self> },
    Optional { inner: Box<Self> },
    Set { item: Box<Self> },
    FrozenSet { item: Box<Self> },
    Tuple { item: Box<Self> },
    Union { variants: Vec<Self> },
}

impl Clone for TypeContainer {
    fn clone(&self) -> Self {
        match self {
            Self::Dataclass(dc) => Self::Dataclass(dc.clone()),
            Self::Primitive(p) => Self::Primitive(p.clone()),
            Self::List { item } => Self::List { item: item.clone() },
            Self::Dict { value } => Self::Dict { value: value.clone() },
            Self::Optional { inner } => Self::Optional { inner: inner.clone() },
            Self::Set { item } => Self::Set { item: item.clone() },
            Self::FrozenSet { item } => Self::FrozenSet { item: item.clone() },
            Self::Tuple { item } => Self::Tuple { item: item.clone() },
            Self::Union { variants } => Self::Union { variants: variants.clone() },
        }
    }
}

impl std::fmt::Debug for TypeContainer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Dataclass(dc) => f.debug_tuple("Dataclass").field(dc).finish(),
            Self::Primitive(_) => write!(f, "Primitive"),
            Self::List { .. } => write!(f, "List"),
            Self::Dict { .. } => write!(f, "Dict"),
            Self::Optional { .. } => write!(f, "Optional"),
            Self::Set { .. } => write!(f, "Set"),
            Self::FrozenSet { .. } => write!(f, "FrozenSet"),
            Self::Tuple { .. } => write!(f, "Tuple"),
            Self::Union { .. } => write!(f, "Union"),
        }
    }
}
