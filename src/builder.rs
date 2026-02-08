use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyString, PyTuple};

use crate::container::{
    DataclassContainer, DataclassField, FieldCommon,
    FieldContainer, IntEnumDumperData, IntEnumLoaderData, PrimitiveContainer,
    StrEnumDumperData, StrEnumLoaderData, TypeContainer,
};
use crate::fields::collection::CollectionKind;
use crate::fields::datetime::parse_datetime_format;

#[pyclass]
pub struct Container {
    inner: TypeContainer,
}

#[pymethods]
impl Container {
    fn load(&self, py: Python<'_>, data: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        self.inner
            .load_from_py(py, data)
            .map_err(|e| e.to_validation_err(py))
    }

    fn dump(&self, py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        self.inner
            .dump_to_py(obj)
            .map_err(|e| e.to_validation_err(py))
    }
}

#[pyclass]
#[derive(Clone, Copy)]
pub struct FieldHandle(pub usize);

#[pymethods]
impl FieldHandle {
    #[allow(clippy::trivially_copy_pass_by_ref)]
    fn __repr__(&self) -> String {
        format!("FieldHandle({})", self.0)
    }
}

#[pyclass]
#[derive(Clone, Copy)]
pub struct DataclassHandle(pub usize);

#[pymethods]
impl DataclassHandle {
    #[allow(clippy::trivially_copy_pass_by_ref)]
    fn __repr__(&self) -> String {
        format!("DataclassHandle({})", self.0)
    }
}

#[pyclass]
#[derive(Clone, Copy)]
pub struct TypeHandle(pub usize);

#[pymethods]
impl TypeHandle {
    #[allow(clippy::trivially_copy_pass_by_ref)]
    fn __repr__(&self) -> String {
        format!("TypeHandle({})", self.0)
    }
}

struct BuilderField {
    name: String,
    name_interned: Py<PyString>,
    data_key: Option<String>,
    data_key_interned: Option<Py<PyString>>,
    slot_offset: Option<isize>,
    field_init: bool,
    container: FieldContainer,
}

#[pyclass]
pub struct ContainerBuilder {
    fields: Vec<BuilderField>,
    dataclasses: Vec<DataclassContainer>,
    types: Vec<TypeContainer>,
    global_decimal_places: Option<i32>,
}

fn extract_optional_py(kwargs: &Bound<'_, PyAny>, key: &str) -> Option<Py<PyAny>> {
    kwargs
        .get_item(key)
        .ok()
        .filter(|value| !value.is_none())
        .map(Bound::unbind)
}

fn extract_optional_string(kwargs: &Bound<'_, PyAny>, key: &str) -> PyResult<Option<String>> {
    if let Ok(value) = kwargs.get_item(key)
        && !value.is_none()
    {
        return Ok(Some(value.extract()?));
    }
    Ok(None)
}

fn extract_optional_py_string(kwargs: &Bound<'_, PyAny>, key: &str) -> PyResult<Option<Py<PyString>>> {
    if let Ok(value) = kwargs.get_item(key)
        && !value.is_none()
    {
        let s: String = value.extract()?;
        return Ok(Some(PyString::new(value.py(), &s).unbind()));
    }
    Ok(None)
}

fn extract_bool(kwargs: &Bound<'_, PyAny>, key: &str, default: bool) -> PyResult<bool> {
    if let Ok(value) = kwargs.get_item(key)
        && !value.is_none()
    {
        return value.extract();
    }
    Ok(default)
}

fn extract_optional_isize(kwargs: &Bound<'_, PyAny>, key: &str) -> PyResult<Option<isize>> {
    if let Ok(value) = kwargs.get_item(key)
        && !value.is_none()
    {
        return Ok(Some(value.extract()?));
    }
    Ok(None)
}

fn get_kwargs<'py>(py: Python<'py>, kwargs: Option<&Bound<'py, PyAny>>) -> Bound<'py, PyAny> {
    kwargs.cloned().unwrap_or_else(|| py.None().into_bound(py))
}

fn build_field_common(optional: bool, kwargs: &Bound<'_, PyAny>, invalid_error: Py<PyString>) -> PyResult<FieldCommon> {
    let default_value = extract_optional_py(kwargs, "default_value");
    let default_factory = extract_optional_py(kwargs, "default_factory");
    let required_error = extract_optional_py_string(kwargs, "required_error")?;
    let none_error = extract_optional_py_string(kwargs, "none_error")?;
    let validator = extract_optional_py(kwargs, "validator");

    Ok(FieldCommon {
        optional,
        default_value,
        default_factory,
        required_error,
        none_error,
        invalid_error,
        validator,
    })
}

fn build_builder_field(
    py: Python<'_>,
    name: &str,
    kwargs: &Bound<'_, PyAny>,
    container: FieldContainer,
) -> PyResult<BuilderField> {
    let name_interned = PyString::intern(py, name).unbind();
    let data_key = extract_optional_string(kwargs, "data_key")?;
    let data_key_interned = data_key
        .as_ref()
        .map(|k| PyString::intern(py, k).unbind());

    let slot_offset: Option<isize> = extract_optional_isize(kwargs, "slot_offset")?
        .filter(|&offset: &isize| {
            offset
                .cast_unsigned()
                .is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>())
        });

    let field_init = extract_bool(kwargs, "field_init", true)?;

    Ok(BuilderField {
        name: name.to_string(),
        name_interned,
        data_key,
        data_key_interned,
        slot_offset,
        field_init,
        container,
    })
}

#[pymethods]
impl ContainerBuilder {
    #[new]
    #[pyo3(signature = (*, decimal_places=None))]
    const fn new(decimal_places: Option<i32>) -> Self {
        Self {
            fields: Vec::new(),
            dataclasses: Vec::new(),
            types: Vec::new(),
            global_decimal_places: decimal_places,
        }
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn str_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let strip_whitespaces = extract_bool(&kwargs, "strip_whitespaces", false)?;
        let post_load = extract_optional_py(&kwargs, "post_load");
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid string.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Str { common, strip_whitespaces, post_load };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn int_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid integer.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Int { common };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn float_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid number.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Float { common };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn bool_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid boolean.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Bool { common };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn decimal_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid number.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;

        let decimal_places: Option<i32> = kwargs.get_item("decimal_places").map_or_else(
            |_| self.global_decimal_places.or(Some(2)),
            |dp_value| {
                if dp_value.is_none() {
                    None
                } else if let Ok(places) = dp_value.extract::<i32>() {
                    Some(places)
                } else {
                    self.global_decimal_places.or(Some(2))
                }
            },
        ).filter(|&p| p >= 0);
        let rounding = extract_optional_py(&kwargs, "rounding");

        let container = FieldContainer::Decimal {
            common,
            decimal_places,
            rounding,
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn date_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid date.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Date { common };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn time_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid time.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Time { common };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn datetime_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid datetime.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;

        let datetime_format = extract_optional_string(&kwargs, "datetime_format")?;
        let format = parse_datetime_format(datetime_format.as_deref());

        let container = FieldContainer::DateTime { common, format };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn uuid_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid UUID.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Uuid { common };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, **kwargs))]
    fn any_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = intern!(py, "").clone().unbind();
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let container = FieldContainer::Any { common };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, enum_cls, enum_values, enum_name, enum_members_repr, **kwargs))]
    #[allow(clippy::too_many_arguments)]
    fn str_enum_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        enum_cls: Py<PyAny>,
        enum_values: &Bound<'_, PyList>,
        enum_name: Option<String>,
        enum_members_repr: Option<String>,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = intern!(py, "").clone().unbind();
        let common = build_field_common(optional, &kwargs, invalid_error)?;

        let values: Vec<(String, Py<PyAny>)> = enum_values
            .iter()
            .map(|item| {
                let tuple: &Bound<'_, PyTuple> = item.cast()?;
                let key: String = tuple.get_item(0)?.extract()?;
                let member: Py<PyAny> = tuple.get_item(1)?.extract()?;
                Ok((key, member))
            })
            .collect::<PyResult<_>>()?;

        let container = FieldContainer::StrEnum {
            common,
            loader_data: Box::new(StrEnumLoaderData { values }),
            dumper_data: Box::new(StrEnumDumperData {
                enum_cls,
                enum_name,
                enum_members_repr,
            }),
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, enum_cls, enum_values, enum_name, enum_members_repr, **kwargs))]
    #[allow(clippy::too_many_arguments)]
    fn int_enum_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        enum_cls: Py<PyAny>,
        enum_values: &Bound<'_, PyList>,
        enum_name: Option<String>,
        enum_members_repr: Option<String>,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = intern!(py, "").clone().unbind();
        let common = build_field_common(optional, &kwargs, invalid_error)?;

        let values: Vec<(Py<PyAny>, Py<PyAny>)> = enum_values
            .iter()
            .map(|item| {
                let tuple: &Bound<'_, PyTuple> = item.cast()?;
                let key: Py<PyAny> = tuple.get_item(0)?.extract()?;
                let member: Py<PyAny> = tuple.get_item(1)?.extract()?;
                Ok((key, member))
            })
            .collect::<PyResult<_>>()?;

        let container = FieldContainer::IntEnum {
            common,
            loader_data: Box::new(IntEnumLoaderData { values }),
            dumper_data: Box::new(IntEnumDumperData {
                enum_cls,
                enum_name,
                enum_members_repr,
            }),
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, item, **kwargs))]
    fn list_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        item: FieldHandle,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid list.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let item_validator = extract_optional_py(&kwargs, "item_validator");

        let item_container = self.fields.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid FieldHandle: {}",
                item.0
            ))
        })?.container.clone();

        let container = FieldContainer::Collection {
            common,
            kind: CollectionKind::List,
            item: Box::new(item_container),
            item_validator,
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, item, **kwargs))]
    fn set_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        item: FieldHandle,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid set.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let item_validator = extract_optional_py(&kwargs, "item_validator");

        let item_container = self.fields.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid FieldHandle: {}",
                item.0
            ))
        })?.container.clone();

        let container = FieldContainer::Collection {
            common,
            kind: CollectionKind::Set,
            item: Box::new(item_container),
            item_validator,
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, item, **kwargs))]
    fn frozenset_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        item: FieldHandle,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid frozenset.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let item_validator = extract_optional_py(&kwargs, "item_validator");

        let item_container = self.fields.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid FieldHandle: {}",
                item.0
            ))
        })?.container.clone();

        let container = FieldContainer::Collection {
            common,
            kind: CollectionKind::FrozenSet,
            item: Box::new(item_container),
            item_validator,
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, item, **kwargs))]
    fn tuple_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        item: FieldHandle,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid tuple.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let item_validator = extract_optional_py(&kwargs, "item_validator");

        let item_container = self.fields.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid FieldHandle: {}",
                item.0
            ))
        })?.container.clone();

        let container = FieldContainer::Collection {
            common,
            kind: CollectionKind::Tuple,
            item: Box::new(item_container),
            item_validator,
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, value, **kwargs))]
    fn dict_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        value: FieldHandle,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = extract_optional_py_string(&kwargs, "invalid_error")?
            .unwrap_or_else(|| intern!(py, "Not a valid dict.").clone().unbind());
        let common = build_field_common(optional, &kwargs, invalid_error)?;
        let value_validator = extract_optional_py(&kwargs, "value_validator");

        let value_container = self.fields.get(value.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid FieldHandle: {}",
                value.0
            ))
        })?.container.clone();

        let container = FieldContainer::Dict {
            common,
            value: Box::new(value_container),
            value_validator,
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, nested, **kwargs))]
    fn nested_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        nested: DataclassHandle,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = intern!(py, "").clone().unbind();
        let common = build_field_common(optional, &kwargs, invalid_error)?;

        let nested_container = self.dataclasses.get(nested.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid DataclassHandle: {}",
                nested.0
            ))
        })?.clone();

        let container = FieldContainer::Nested {
            common,
            container: Box::new(nested_container),
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (name, optional, variants, **kwargs))]
    fn union_field(
        &mut self,
        py: Python<'_>,
        name: &str,
        optional: bool,
        variants: Vec<FieldHandle>,
        kwargs: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<FieldHandle> {
        let kwargs = get_kwargs(py, kwargs);
        let invalid_error = intern!(py, "").clone().unbind();
        let common = build_field_common(optional, &kwargs, invalid_error)?;

        let mut variant_containers = Vec::with_capacity(variants.len());
        for handle in variants {
            let variant = self.fields.get(handle.0).ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Invalid FieldHandle: {}",
                    handle.0
                ))
            })?.container.clone();
            variant_containers.push(variant);
        }

        let container = FieldContainer::Union {
            common,
            variants: variant_containers,
        };
        let builder_field = build_builder_field(py, name, &kwargs, container)?;

        let idx = self.fields.len();
        self.fields.push(builder_field);
        Ok(FieldHandle(idx))
    }

    #[pyo3(signature = (cls, fields, *, can_use_direct_slots=false, has_post_init=false, ignore_none=true))]
    fn dataclass(
        &mut self,
        py: Python<'_>,
        cls: Py<PyAny>,
        fields: Vec<FieldHandle>,
        can_use_direct_slots: bool,
        has_post_init: bool,
        ignore_none: bool,
    ) -> PyResult<DataclassHandle> {
        let mut container = DataclassContainer::new(cls, can_use_direct_slots, has_post_init, ignore_none);

        for handle in fields {
            let builder_field = self.fields.get(handle.0).ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Invalid FieldHandle: {}",
                    handle.0
                ))
            })?;

            let dc_field = DataclassField {
                name: builder_field.name.clone(),
                name_interned: builder_field.name_interned.clone_ref(py),
                data_key: builder_field.data_key.clone(),
                data_key_interned: builder_field.data_key_interned.as_ref().map(|v| v.clone_ref(py)),
                slot_offset: builder_field.slot_offset,
                field_init: builder_field.field_init,
                field: builder_field.container.clone(),
            };
            container.add_field(dc_field);
        }

        let idx = self.dataclasses.len();
        self.dataclasses.push(container);
        Ok(DataclassHandle(idx))
    }

    fn type_dataclass(&mut self, dc: DataclassHandle) -> PyResult<TypeHandle> {
        let container = self.dataclasses.get(dc.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid DataclassHandle: {}",
                dc.0
            ))
        })?.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::Dataclass(container));
        Ok(TypeHandle(idx))
    }

    fn type_primitive(&mut self, field: FieldHandle) -> PyResult<TypeHandle> {
        let field_container = self.fields.get(field.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid FieldHandle: {}",
                field.0
            ))
        })?.container.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::Primitive(PrimitiveContainer {
            field: field_container,
        }));
        Ok(TypeHandle(idx))
    }

    fn type_list(&mut self, item: TypeHandle) -> PyResult<TypeHandle> {
        let item_container = self.types.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid TypeHandle: {}",
                item.0
            ))
        })?.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::List {
            item: Box::new(item_container),
        });
        Ok(TypeHandle(idx))
    }

    fn type_dict(&mut self, value: TypeHandle) -> PyResult<TypeHandle> {
        let value_container = self.types.get(value.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid TypeHandle: {}",
                value.0
            ))
        })?.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::Dict {
            value: Box::new(value_container),
        });
        Ok(TypeHandle(idx))
    }

    fn type_optional(&mut self, inner: TypeHandle) -> PyResult<TypeHandle> {
        let inner_container = self.types.get(inner.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid TypeHandle: {}",
                inner.0
            ))
        })?.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::Optional {
            inner: Box::new(inner_container),
        });
        Ok(TypeHandle(idx))
    }

    fn type_set(&mut self, item: TypeHandle) -> PyResult<TypeHandle> {
        let item_container = self.types.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid TypeHandle: {}",
                item.0
            ))
        })?.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::Set {
            item: Box::new(item_container),
        });
        Ok(TypeHandle(idx))
    }

    fn type_frozenset(&mut self, item: TypeHandle) -> PyResult<TypeHandle> {
        let item_container = self.types.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid TypeHandle: {}",
                item.0
            ))
        })?.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::FrozenSet {
            item: Box::new(item_container),
        });
        Ok(TypeHandle(idx))
    }

    fn type_tuple(&mut self, item: TypeHandle) -> PyResult<TypeHandle> {
        let item_container = self.types.get(item.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid TypeHandle: {}",
                item.0
            ))
        })?.clone();

        let idx = self.types.len();
        self.types.push(TypeContainer::Tuple {
            item: Box::new(item_container),
        });
        Ok(TypeHandle(idx))
    }

    fn type_union(&mut self, variants: Vec<TypeHandle>) -> PyResult<TypeHandle> {
        let mut variant_containers = Vec::with_capacity(variants.len());
        for handle in variants {
            let container = self.types.get(handle.0).ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Invalid TypeHandle: {}",
                    handle.0
                ))
            })?.clone();
            variant_containers.push(container);
        }

        let idx = self.types.len();
        self.types.push(TypeContainer::Union {
            variants: variant_containers,
        });
        Ok(TypeHandle(idx))
    }

    fn build(&mut self, type_handle: TypeHandle) -> PyResult<Container> {
        let inner = self.types.get(type_handle.0).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid TypeHandle: {}",
                type_handle.0
            ))
        })?.clone();

        Ok(Container { inner })
    }
}
