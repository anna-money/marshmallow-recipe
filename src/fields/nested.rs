use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::PyString;

use super::helpers::{err_dict_from_list, field_error, json_field_error, NESTED_ERROR};
use crate::cache::get_cached_types;
use crate::slots::set_slot_value_direct;
use crate::types::{DumpContext, LoadContext};
use crate::utils::{call_validator, extract_error_args, pyany_to_json_value, wrap_err_dict};

pub struct DataclassDumperSchema {
    pub cls: Py<PyAny>,
    pub fields: Vec<FieldDumper>,
    pub field_lookup: HashMap<String, usize>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
}

impl Clone for DataclassDumperSchema {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
        })
    }
}

pub struct FieldDumper {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub data_key: Option<String>,
    pub dumper: crate::dumper::Dumper,
    pub optional: bool,
    pub slot_offset: Option<isize>,
    pub validator: Option<Py<PyAny>>,
}

impl std::fmt::Debug for FieldDumper {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FieldDumper")
            .field("name", &self.name)
            .field("optional", &self.optional)
            .finish_non_exhaustive()
    }
}

impl Clone for FieldDumper {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            name: self.name.clone(),
            name_interned: self.name_interned.clone_ref(py),
            data_key: self.data_key.clone(),
            dumper: self.dumper.clone(),
            optional: self.optional,
            slot_offset: self.slot_offset,
            validator: self.validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

pub struct DataclassLoaderSchema {
    pub cls: Py<PyAny>,
    pub fields: Vec<FieldLoader>,
    pub field_lookup: HashMap<String, usize>,
    pub can_use_direct_slots: bool,
    pub has_post_init: bool,
}

impl Clone for DataclassLoaderSchema {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            cls: self.cls.clone_ref(py),
            fields: self.fields.clone(),
            field_lookup: self.field_lookup.clone(),
            can_use_direct_slots: self.can_use_direct_slots,
            has_post_init: self.has_post_init,
        })
    }
}

pub struct FieldLoader {
    pub name: String,
    pub name_interned: Py<PyString>,
    pub data_key: Option<String>,
    pub loader: crate::loader::Loader,
    pub optional: bool,
    pub slot_offset: Option<isize>,
    pub default_value: Option<Py<PyAny>>,
    pub default_factory: Option<Py<PyAny>>,
    pub required_error: Option<String>,
    pub none_error: Option<String>,
    pub invalid_error: Option<String>,
    pub field_init: bool,
    pub post_load: Option<Py<PyAny>>,
    pub validator: Option<Py<PyAny>>,
    pub item_validator: Option<Py<PyAny>>,
    pub value_validator: Option<Py<PyAny>>,
}

impl Clone for FieldLoader {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            name: self.name.clone(),
            name_interned: self.name_interned.clone_ref(py),
            data_key: self.data_key.clone(),
            loader: self.loader.clone(),
            optional: self.optional,
            slot_offset: self.slot_offset,
            default_value: self.default_value.as_ref().map(|v| v.clone_ref(py)),
            default_factory: self.default_factory.as_ref().map(|f| f.clone_ref(py)),
            required_error: self.required_error.clone(),
            none_error: self.none_error.clone(),
            invalid_error: self.invalid_error.clone(),
            field_init: self.field_init,
            post_load: self.post_load.as_ref().map(|v| v.clone_ref(py)),
            validator: self.validator.as_ref().map(|v| v.clone_ref(py)),
            item_validator: self.item_validator.as_ref().map(|v| v.clone_ref(py)),
            value_validator: self.value_validator.as_ref().map(|v| v.clone_ref(py)),
        })
    }
}

impl std::fmt::Debug for FieldLoader {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FieldLoader")
            .field("name", &self.name)
            .field("optional", &self.optional)
            .finish_non_exhaustive()
    }
}

pub mod nested_dumper {
    use pyo3::prelude::*;
    use pyo3::types::PyDict;
    use serde_json::Value;

    use super::{
        call_validator, err_dict_from_list, field_error, get_cached_types, json_field_error,
        pyany_to_json_value, DataclassDumperSchema, DumpContext, FieldDumper, NESTED_ERROR,
    };

    #[inline]
    pub fn can_dump<'py>(
        value: &Bound<'py, PyAny>,
        ctx: &DumpContext<'_, 'py>,
        schema: &DataclassDumperSchema,
    ) -> bool {
        value.is_instance(schema.cls.bind(ctx.py)).unwrap_or(false)
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        schema: &DataclassDumperSchema,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance(schema.cls.bind(ctx.py))? {
            return Err(field_error(ctx.py, field_name, NESTED_ERROR));
        }
        dump_dataclass(value, &schema.fields, ctx)
    }

    pub fn dump_dataclass<'py>(
        obj: &Bound<'py, PyAny>,
        fields: &[FieldDumper],
        ctx: &DumpContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        let ignore_none = ctx.none_value_handling.is_none_or(|s| s == "ignore");

        let cached = get_cached_types(ctx.py)?;
        let missing_sentinel = cached.missing_sentinel.bind(ctx.py);
        let result = PyDict::new(ctx.py);

        for field in fields {
            let py_value = match field.slot_offset {
                Some(offset) => match unsafe { crate::slots::get_slot_value_direct(ctx.py, obj, offset) } {
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

            let key = field.data_key.as_ref().unwrap_or(&field.name);

            let dumped_value = if py_value.is_none() {
                ctx.py.None()
            } else {
                field.dumper.dump_to_dict(&py_value, &field.name, ctx)?
            };
            result.set_item(key.as_str(), dumped_value)?;
        }

        Ok(result.into_any().unbind())
    }

    struct FieldValueDumper<'a, 'py> {
        value: &'a Bound<'py, PyAny>,
        dumper: &'a crate::dumper::Dumper,
        field_name: &'a str,
        ctx: &'a DumpContext<'a, 'py>,
    }

    impl serde::Serialize for FieldValueDumper<'_, '_> {
        fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
            self.dumper.dump(self.value, self.field_name, self.ctx, serializer)
        }
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, '_>,
        schema: &DataclassDumperSchema,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        if !value.is_instance(schema.cls.bind(ctx.py)).map_err(|e| S::Error::custom(e.to_string()))? {
            return Err(S::Error::custom(json_field_error(field_name, NESTED_ERROR)));
        }
        dump_dataclass_to_serializer(value, &schema.fields, ctx, serializer)
    }

    pub fn dump_dataclass_to_serializer<S: serde::Serializer>(
        obj: &Bound<'_, PyAny>,
        fields: &[FieldDumper],
        ctx: &DumpContext<'_, '_>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::{Error, SerializeMap};

        let ignore_none = ctx.none_value_handling.is_none_or(|s| s == "ignore");

        let cached = get_cached_types(ctx.py).map_err(|e| S::Error::custom(e.to_string()))?;
        let missing_sentinel = cached.missing_sentinel.bind(ctx.py);

        let mut map = serializer.serialize_map(None)?;

        for field in fields {
            let py_value = match field.slot_offset {
                Some(offset) => match unsafe { crate::slots::get_slot_value_direct(ctx.py, obj, offset) } {
                    Some(value) => value,
                    None => obj.getattr(field.name.as_str()).map_err(|e| S::Error::custom(e.to_string()))?,
                },
                None => obj.getattr(field.name.as_str()).map_err(|e| S::Error::custom(e.to_string()))?,
            };

            if py_value.is(missing_sentinel) || (py_value.is_none() && ignore_none) {
                continue;
            }

            if let Some(ref validator) = field.validator {
                if let Some(errors) = call_validator(ctx.py, validator, &py_value).map_err(|e| S::Error::custom(e.to_string()))? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut err_map = serde_json::Map::new();
                    err_map.insert(field.name.clone(), errors_json);
                    return Err(S::Error::custom(Value::Object(err_map).to_string()));
                }
            }

            let key = field.data_key.as_ref().unwrap_or(&field.name);

            if py_value.is_none() {
                map.serialize_entry(key.as_str(), &())?;
            } else {
                map.serialize_entry(key.as_str(), &FieldValueDumper {
                    value: &py_value,
                    dumper: &field.dumper,
                    field_name: &field.name,
                    ctx,
                })?;
            }
        }

        map.end()
    }
}

pub mod nested_loader {
    use std::collections::HashMap;

    use pyo3::intern;
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyString};
    use smallbitvec::SmallBitVec;

    use super::{
        call_validator, extract_error_args, field_error, get_cached_types, set_slot_value_direct,
        wrap_err_dict, DataclassLoaderSchema, FieldLoader, LoadContext, NESTED_ERROR,
    };
    use crate::loader::Loader;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
        schema: &DataclassLoaderSchema,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDict>() {
            return Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(NESTED_ERROR)));
        }
        load_dataclass(value, schema, ctx).map_err(|e| {
            let inner = extract_error_args(ctx.py, &e);
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                wrap_err_dict(ctx.py, field_name, inner),
            )
        })
    }

    pub fn load_dataclass<'py>(
        value: &Bound<'py, PyAny>,
        schema: &DataclassLoaderSchema,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        let dict = value.cast::<PyDict>().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a dict for dataclass")
        })?;
        let cls = schema.cls.bind(ctx.py);
        if schema.can_use_direct_slots {
            load_dataclass_direct_slots(dict, cls, &schema.fields, &schema.field_lookup, ctx)
        } else {
            load_dataclass_kwargs(dict, cls, &schema.fields, &schema.field_lookup, ctx)
        }
    }

    pub fn load_dataclass_from_parts<'py>(
        value: &Bound<'py, PyAny>,
        cls: &Bound<'py, PyAny>,
        fields: &[FieldLoader],
        field_lookup: &HashMap<String, usize>,
        can_use_direct_slots: bool,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        let dict = value.cast::<PyDict>().map_err(|_| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected a dict for dataclass")
        })?;
        if can_use_direct_slots {
            load_dataclass_direct_slots(dict, cls, fields, field_lookup, ctx)
        } else {
            load_dataclass_kwargs(dict, cls, fields, field_lookup, ctx)
        }
    }

    fn load_dataclass_kwargs<'py>(
        dict: &Bound<'py, PyDict>,
        cls: &Bound<'py, PyAny>,
        fields: &[FieldLoader],
        field_lookup: &HashMap<String, usize>,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        let kwargs = PyDict::new(ctx.py);
        let mut seen_fields = SmallBitVec::from_elem(fields.len(), false);

        for (key, value) in dict.iter() {
            let key_str = key.cast::<PyString>()?.to_str()?;
            if let Some(&idx) = field_lookup.get(key_str) {
                let field = &fields[idx];
                seen_fields.set(idx, true);
                if !field.field_init {
                    continue;
                }
                let loaded = load_field_value(&value, field, ctx)?;
                let validated = apply_post_load_and_validate(loaded, field, ctx)?;
                kwargs.set_item(field.name_interned.bind(ctx.py), validated)?;
            }
        }

        for (idx, field) in fields.iter().enumerate() {
            if !seen_fields[idx] && field.field_init {
                if let Some(value) = get_default_value(field, ctx)? {
                    kwargs.set_item(field.name_interned.bind(ctx.py), value)?;
                } else {
                    let msg = field.required_error.as_deref().unwrap_or("Missing data for required field.");
                    return Err(field_error(ctx.py, &field.name, msg));
                }
            }
        }

        cls.call((), Some(&kwargs)).map(pyo3::Bound::unbind)
    }

    fn load_dataclass_direct_slots<'py>(
        dict: &Bound<'py, PyDict>,
        cls: &Bound<'py, PyAny>,
        fields: &[FieldLoader],
        field_lookup: &HashMap<String, usize>,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        let cached_types = get_cached_types(ctx.py)?;
        let object_type = cached_types.object_cls.bind(ctx.py);
        let instance = object_type.call_method1(intern!(ctx.py, "__new__"), (cls,))?;

        let mut field_values: Vec<Option<Py<PyAny>>> = (0..fields.len()).map(|_| None).collect();

        for (key, value) in dict.iter() {
            let key_str = key.cast::<PyString>()?.to_str()?;
            if let Some(&idx) = field_lookup.get(key_str) {
                let field = &fields[idx];
                let loaded = load_field_value(&value, field, ctx)?;
                let validated = apply_post_load_and_validate(loaded, field, ctx)?;
                field_values[idx] = Some(validated);
            }
        }

        for (idx, field) in fields.iter().enumerate() {
            let py_value = if let Some(value) = field_values[idx].take() {
                value
            } else if let Some(default) = get_default_value(field, ctx)? {
                default
            } else {
                let msg = field.required_error.as_deref().unwrap_or("Missing data for required field.");
                return Err(field_error(ctx.py, &field.name, msg));
            };

            if let Some(offset) = field.slot_offset {
                unsafe {
                    set_slot_value_direct(&instance, offset, py_value);
                }
            } else {
                instance.setattr(field.name_interned.bind(ctx.py), py_value)?;
            }
        }

        Ok(instance.unbind())
    }

    pub fn load_field_value<'py>(
        value: &Bound<'py, PyAny>,
        field: &FieldLoader,
        ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        if matches!(field.loader, Loader::Any) {
            return Ok(value.clone().unbind());
        }

        if value.is_none() {
            if !field.optional {
                let msg = field.none_error.as_deref().unwrap_or("Field may not be null.");
                return Err(field_error(ctx.py, &field.name, msg));
            }
            return Ok(ctx.py.None());
        }

        field.loader.load_from_dict(value, &field.name, field.invalid_error.as_deref(), ctx)
    }

    fn get_default_value(field: &FieldLoader, ctx: &LoadContext<'_>) -> PyResult<Option<Py<PyAny>>> {
        if let Some(ref factory) = field.default_factory {
            return Ok(Some(factory.call0(ctx.py)?));
        }
        if let Some(ref value) = field.default_value {
            return Ok(Some(value.clone_ref(ctx.py)));
        }
        Ok(field.optional.then(|| ctx.py.None()))
    }

    fn apply_post_load_and_validate(
        value: Py<PyAny>,
        field: &FieldLoader,
        ctx: &LoadContext<'_>,
    ) -> PyResult<Py<PyAny>> {
        let mut result = value;

        if let Some(ref post_load_fn) = field.post_load {
            result = post_load_fn.call1(ctx.py, (result,))?;
        }

        if let Some(ref validator) = field.validator {
            if let Some(errors) = call_validator(ctx.py, validator, result.bind(ctx.py))? {
                let dict = PyDict::new(ctx.py);
                dict.set_item(&field.name, errors).unwrap();
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(dict.into_any().unbind()));
            }
        }

        Ok(result)
    }
}
