use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList, PyMapping, PySet, PyString, PyTuple};
use smallbitvec::SmallBitVec;

use crate::container::{
    DataclassContainer, DataclassField, DataclassRegistry, FieldCommon, FieldContainer,
    LoadStrategy, TypeContainer,
};
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
use crate::fields::{
    any, bool_literal, bool_type, bytes, collection, date, datetime, decimal, dict, float_type,
    int_enum, int_literal, int_type, str_enum, str_literal, str_type, time, union, uuid,
};
use crate::slots::set_slot_value_direct;
use crate::utils::{
    call_validator, extract_error_args, get_mapping_abc, get_missing_sentinel, get_object_cls,
    new_presized_list,
};

const NESTED_ERROR: &str = "Invalid input type.";

fn call_validator_with_error(
    validator: &Py<PyAny>,
    value: &Bound<'_, PyAny>,
) -> Result<(), SerializationError> {
    let py = value.py();
    match call_validator(py, validator, value) {
        Ok(None) => Ok(()),
        Ok(Some(errors)) => Err(pyerrors_to_serialization_error(py, &errors)),
        Err(e) => {
            let error_value = extract_error_args(py, &e);
            Err(pyerrors_to_serialization_error(py, &error_value))
        }
    }
}

#[allow(clippy::cast_sign_loss)]
impl FieldContainer {
    pub fn load_from_py(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let py = value.py();
        let common = self.common();

        if value.is_none() {
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
                min_length,
                max_length,
                regexp,
                ..
            } => str_type::load_from_py(
                value,
                *strip_whitespaces,
                common.optional,
                &common.invalid_error,
                post_load.as_ref(),
                min_length.as_ref(),
                max_length.as_ref(),
                regexp.as_ref(),
            ),
            Self::Int {
                gt, gte, lt, lte, ..
            } => int_type::load_from_py(
                value,
                &common.invalid_error,
                gt.as_ref(),
                gte.as_ref(),
                lt.as_ref(),
                lte.as_ref(),
            ),
            Self::Float {
                gt, gte, lt, lte, ..
            } => float_type::load_from_py(
                value,
                &common.invalid_error,
                gt.as_ref(),
                gte.as_ref(),
                lt.as_ref(),
                lte.as_ref(),
            ),
            Self::Bool { .. } => bool_type::load_from_py(value, &common.invalid_error),
            Self::Decimal {
                decimal_places,
                rounding,
                gt,
                gte,
                lt,
                lte,
                ..
            } => decimal::load_from_py(
                value,
                *decimal_places,
                rounding.as_ref(),
                &common.invalid_error,
                gt.as_ref(),
                gte.as_ref(),
                lt.as_ref(),
                lte.as_ref(),
            ),
            Self::Date { .. } => date::load_from_py(value, &common.invalid_error),
            Self::Time { .. } => time::load_from_py(value, &common.invalid_error),
            Self::DateTime { format, .. } => {
                datetime::load_from_py(value, format, &common.invalid_error)
            }
            Self::Uuid { .. } => uuid::load_from_py(value, &common.invalid_error),
            Self::Bytes { .. } => bytes::load_from_py(value, &common.invalid_error),
            Self::StrEnum {
                common,
                enum_values,
                ..
            } => str_enum::load_from_py(value, enum_values, &common.invalid_error),
            Self::IntEnum {
                common,
                enum_values,
                ..
            } => int_enum::load_from_py(value, enum_values, &common.invalid_error),
            Self::StrLiteral { common, values } => {
                str_literal::load_from_py(value, values, &common.invalid_error)
            }
            Self::IntLiteral { common, values } => {
                int_literal::load_from_py(value, values, &common.invalid_error)
            }
            Self::BoolLiteral { common, values } => {
                bool_literal::load_from_py(value, values, &common.invalid_error)
            }
            Self::Any { .. } => Ok(any::load_from_py(value)),
            Self::Collection {
                kind,
                item,
                item_validator,
                min_length,
                max_length,
                ..
            } => collection::load_from_py(
                registry,
                value,
                *kind,
                item,
                item_validator.as_ref(),
                &common.invalid_error,
                min_length.as_ref(),
                max_length.as_ref(),
            ),
            Self::Dict {
                value: value_schema,
                value_validator,
                ..
            } => dict::load_from_py(
                registry,
                value,
                value_schema,
                value_validator.as_ref(),
                &common.invalid_error,
            ),
            Self::Nested {
                dataclass_index, ..
            } => registry.get(*dataclass_index).load_from_py(registry, value),
            Self::Union { variants, .. } => union::load_from_py(registry, value, variants),
        }
    }
}

impl DataclassContainer {
    pub fn load_from_py(
        &self,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let py = value.py();

        if let Ok(dict) = value.cast::<PyDict>() {
            let dict = apply_pre_loads(py, dict, &self.pre_loads)?;
            return match self.load_strategy {
                LoadStrategy::DirectSlots => self.load_from_py_direct_slots(registry, &dict),
                LoadStrategy::DirectDict => self.load_from_py_direct_dict(registry, &dict),
                LoadStrategy::Kwargs => self.load_from_py_kwargs(registry, &dict),
            };
        }

        let mapping_abc =
            get_mapping_abc(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !value.is_instance(mapping_abc).unwrap_or(false) {
            let err_dict = PyDict::new(py);
            let _ = err_dict.set_item(
                "_schema",
                PyList::new(py, [intern!(py, NESTED_ERROR)]).unwrap(),
            );
            return Err(SerializationError::Dict(err_dict.unbind()));
        }

        if !self.pre_loads.is_empty() {
            let coerced = coerce_to_pydict(py, value)?;
            let dict = apply_pre_loads(py, &coerced, &self.pre_loads)?;
            return match self.load_strategy {
                LoadStrategy::DirectSlots => self.load_from_py_direct_slots(registry, &dict),
                LoadStrategy::DirectDict => self.load_from_py_direct_dict(registry, &dict),
                LoadStrategy::Kwargs => self.load_from_py_kwargs(registry, &dict),
            };
        }

        match self.load_strategy {
            LoadStrategy::DirectSlots => {
                self.load_from_py_direct_slots_from_mapping(registry, value)
            }
            LoadStrategy::DirectDict => self.load_from_py_direct_dict_from_mapping(registry, value),
            LoadStrategy::Kwargs => self.load_from_py_kwargs_from_mapping(registry, value),
        }
    }

    fn collect_fields_into_dict<'py>(
        &self,
        registry: &DataclassRegistry,
        dict: &Bound<'py, PyDict>,
    ) -> Result<Bound<'py, PyDict>, SerializationError> {
        let py = dict.py();
        let result = PyDict::new(py);
        let mut seen = SmallBitVec::from_elem(self.fields.len(), false);
        let mut errors: Option<Bound<'_, PyDict>> = None;

        for (k, v) in dict.iter() {
            let key_str = k
                .cast::<PyString>()
                .ok()
                .and_then(|s| s.to_str().ok())
                .unwrap_or("");

            if let Some(&idx) = self.field_lookup.get(key_str) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();
                seen.set(idx, true);

                if !dc_field.field_init {
                    continue;
                }

                match dc_field.field.load_from_py(registry, &v) {
                    Ok(py_val) => match apply_validate(py, py_val, common.validator.as_ref()) {
                        Ok(validated) => {
                            let _ = result.set_item(dc_field.name_interned.bind(py), validated);
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
                        let _ = result.set_item(dc_field.name_interned.bind(py), val);
                    }
                    Ok(None) => push_required_error(
                        py,
                        &mut errors,
                        dc_field.name_interned.bind(py),
                        common,
                    ),
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                    }
                }
            }
        }

        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }

        Ok(result)
    }

    fn load_from_py_kwargs(
        &self,
        registry: &DataclassRegistry,
        dict: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let kwargs = self.collect_fields_into_dict(registry, dict)?;
        self.instantiate_via_kwargs(dict.py(), &kwargs)
    }

    fn load_from_py_direct_dict(
        &self,
        registry: &DataclassRegistry,
        dict: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let result_dict = self.collect_fields_into_dict(registry, dict)?;
        self.instantiate_via_direct_dict(dict.py(), &result_dict)
    }

    fn instantiate_via_kwargs(
        &self,
        py: Python<'_>,
        kwargs: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, SerializationError> {
        self.cls
            .bind(py)
            .call((), Some(kwargs))
            .map(Bound::unbind)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))
    }

    fn instantiate_via_direct_dict(
        &self,
        py: Python<'_>,
        result_dict: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let object_type =
            get_object_cls(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let instance = object_type
            .call_method1(intern!(py, "__new__"), (self.cls.bind(py),))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        object_type
            .call_method1(
                intern!(py, "__setattr__"),
                (&instance, intern!(py, "__dict__"), result_dict),
            )
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        Ok(instance.unbind())
    }

    fn load_from_py_direct_slots(
        &self,
        registry: &DataclassRegistry,
        dict: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let py = dict.py();
        let object_type =
            get_object_cls(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let instance = object_type
            .call_method1(intern!(py, "__new__"), (self.cls.bind(py),))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;

        let mut field_values: Vec<Option<Py<PyAny>>> =
            (0..self.fields.len()).map(|_| None).collect();
        let mut errors: Option<Bound<'_, PyDict>> = None;

        for (k, v) in dict.iter() {
            let key_str = k
                .cast::<PyString>()
                .ok()
                .and_then(|s| s.to_str().ok())
                .unwrap_or("");

            if let Some(&idx) = self.field_lookup.get(key_str) {
                let dc_field = &self.fields[idx];
                let common = dc_field.field.common();

                match dc_field.field.load_from_py(registry, &v) {
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
                        push_required_error(
                            py,
                            &mut errors,
                            dc_field.name_interned.bind(py),
                            common,
                        );
                        continue;
                    }
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        continue;
                    }
                }
            };

            write_field_to_slot_or_attr(py, &instance, dc_field, py_value, &mut errors)?;
        }

        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }

        Ok(instance.unbind())
    }

    fn collect_fields_into_dict_from_mapping<'py>(
        &self,
        registry: &DataclassRegistry,
        data: &Bound<'py, PyAny>,
    ) -> Result<Bound<'py, PyDict>, SerializationError> {
        let py = data.py();
        let result = PyDict::new(py);
        let mut errors: Option<Bound<'_, PyDict>> = None;
        let missing_sentinel =
            get_missing_sentinel(py).map_err(|e| SerializationError::from_pyerr(py, &e))?;

        for dc_field in &self.fields {
            if !dc_field.field_init {
                continue;
            }
            let common = dc_field.field.common();
            let key = dc_field.data_key_interned.bind(py);
            let present: Option<Bound<'_, PyAny>> = match data.get_item(key) {
                Ok(v) if v.is(missing_sentinel) => None,
                Ok(v) => Some(v),
                Err(e) if e.is_instance_of::<pyo3::exceptions::PyKeyError>(py) => None,
                Err(e) => {
                    accumulate_error(
                        py,
                        &mut errors,
                        dc_field.name_interned.bind(py),
                        &SerializationError::from_pyerr(py, &e),
                    );
                    continue;
                }
            };

            let py_val_result = if let Some(v) = present {
                dc_field
                    .field
                    .load_from_py(registry, &v)
                    .and_then(|loaded| apply_validate(py, loaded, common.validator.as_ref()))
            } else {
                match get_default_value(py, common) {
                    Ok(Some(val)) => Ok(val),
                    Ok(None) => {
                        push_required_error(
                            py,
                            &mut errors,
                            dc_field.name_interned.bind(py),
                            common,
                        );
                        continue;
                    }
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        continue;
                    }
                }
            };

            match py_val_result {
                Ok(val) => {
                    let _ = result.set_item(dc_field.name_interned.bind(py), val);
                }
                Err(ref e) => {
                    accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                }
            }
        }

        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }
        Ok(result)
    }

    fn load_from_py_kwargs_from_mapping(
        &self,
        registry: &DataclassRegistry,
        data: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let kwargs = self.collect_fields_into_dict_from_mapping(registry, data)?;
        self.instantiate_via_kwargs(data.py(), &kwargs)
    }

    fn load_from_py_direct_dict_from_mapping(
        &self,
        registry: &DataclassRegistry,
        data: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let result_dict = self.collect_fields_into_dict_from_mapping(registry, data)?;
        self.instantiate_via_direct_dict(data.py(), &result_dict)
    }

    fn load_from_py_direct_slots_from_mapping(
        &self,
        registry: &DataclassRegistry,
        data: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let py = data.py();
        let object_type =
            get_object_cls(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let instance = object_type
            .call_method1(intern!(py, "__new__"), (self.cls.bind(py),))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        let missing_sentinel =
            get_missing_sentinel(py).map_err(|e| SerializationError::from_pyerr(py, &e))?;

        let mut errors: Option<Bound<'_, PyDict>> = None;

        for dc_field in &self.fields {
            let common = dc_field.field.common();
            let key = dc_field.data_key_interned.bind(py);
            let present: Option<Bound<'_, PyAny>> = match data.get_item(key) {
                Ok(v) if v.is(missing_sentinel) => None,
                Ok(v) => Some(v),
                Err(e) if e.is_instance_of::<pyo3::exceptions::PyKeyError>(py) => None,
                Err(e) => {
                    accumulate_error(
                        py,
                        &mut errors,
                        dc_field.name_interned.bind(py),
                        &SerializationError::from_pyerr(py, &e),
                    );
                    continue;
                }
            };

            let py_value: Py<PyAny> = if let Some(v) = present {
                match dc_field.field.load_from_py(registry, &v) {
                    Ok(val) => match apply_validate(py, val, common.validator.as_ref()) {
                        Ok(validated) => validated,
                        Err(ref e) => {
                            accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                            continue;
                        }
                    },
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        continue;
                    }
                }
            } else {
                match get_default_value(py, common) {
                    Ok(Some(val)) => val,
                    Ok(None) => {
                        push_required_error(
                            py,
                            &mut errors,
                            dc_field.name_interned.bind(py),
                            common,
                        );
                        continue;
                    }
                    Err(ref e) => {
                        accumulate_error(py, &mut errors, dc_field.name_interned.bind(py), e);
                        continue;
                    }
                }
            };

            write_field_to_slot_or_attr(py, &instance, dc_field, py_value, &mut errors)?;
        }

        if let Some(errors) = errors {
            return Err(SerializationError::Dict(errors.unbind()));
        }

        Ok(instance.unbind())
    }
}

fn coerce_to_pydict<'py>(
    py: Python<'py>,
    value: &Bound<'py, PyAny>,
) -> Result<Bound<'py, PyDict>, SerializationError> {
    let mapping = value
        .cast::<PyMapping>()
        .map_err(|_| SerializationError::simple(py, "Mapping required"))?;
    let dict = PyDict::new(py);
    dict.update(mapping)
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    Ok(dict)
}

fn write_field_to_slot_or_attr<'py>(
    py: Python<'py>,
    instance: &Bound<'py, PyAny>,
    dc_field: &DataclassField,
    py_value: Py<PyAny>,
    errors: &mut Option<Bound<'py, PyDict>>,
) -> Result<(), SerializationError> {
    if let Some(offset) = dc_field.slot_offset {
        if !unsafe { set_slot_value_direct(instance, offset, py_value) } {
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
        Ok(())
    } else {
        instance
            .setattr(dc_field.name_interned.bind(py), py_value)
            .map_err(|e| SerializationError::simple(py, &e.to_string()))
    }
}

fn apply_pre_loads<'py>(
    py: Python<'py>,
    dict: &Bound<'py, PyDict>,
    pre_loads: &[Py<PyAny>],
) -> Result<Bound<'py, PyDict>, SerializationError> {
    let Some((first, rest)) = pre_loads.split_first() else {
        return Ok(dict.clone());
    };
    let mut current = call_pre_load(py, dict, first)?;
    for hook in rest {
        current = call_pre_load(py, &current, hook)?;
    }
    Ok(current)
}

fn call_pre_load<'py>(
    py: Python<'py>,
    dict: &Bound<'py, PyDict>,
    hook: &Py<PyAny>,
) -> Result<Bound<'py, PyDict>, SerializationError> {
    hook.call1(py, (dict,))
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?
        .into_bound(py)
        .cast_into::<PyDict>()
        .map_err(|_| SerializationError::simple(py, "pre_load hook must return a dict"))
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

fn push_required_error<'py>(
    py: Python<'py>,
    errors: &mut Option<Bound<'py, PyDict>>,
    name: &Bound<'py, PyString>,
    common: &FieldCommon,
) {
    let err_list = common.required_error.as_ref().map_or_else(
        || PyList::new(py, [intern!(py, "Missing data for required field.")]).unwrap(),
        |s| PyList::new(py, [s.bind(py)]).unwrap(),
    );
    let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
    let _ = err_dict.set_item(name, err_list);
}

impl TypeContainer {
    pub fn load_from_py(
        &self,
        py: Python<'_>,
        registry: &DataclassRegistry,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        match self {
            Self::Dataclass(idx) => registry.get(*idx).load_from_py(registry, value),
            Self::Primitive(p) => {
                if value.is_none() {
                    return Ok(py.None());
                }
                p.field.load_from_py(registry, value)
            }
            Self::List { item } => {
                let list = value.cast::<PyList>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a list").clone().unbind())
                })?;
                let result = new_presized_list(py, list.len());
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (idx, v) in list.iter().enumerate() {
                    match item.load_from_py(py, registry, &v) {
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
                let result = PyDict::new(py);
                let mut errors: Option<Bound<'_, PyDict>> = None;

                let mut handle = |k: Bound<'_, PyAny>, v: Bound<'_, PyAny>| match value_container
                    .load_from_py(py, registry, &v)
                {
                    Ok(py_val) => {
                        let _ = result.set_item(&k, py_val);
                    }
                    Err(ref e) => {
                        let key_str = k
                            .cast::<PyString>()
                            .ok()
                            .and_then(|s| s.to_str().ok())
                            .unwrap_or("");
                        accumulate_error(py, &mut errors, key_str, e);
                    }
                };

                if let Ok(dict) = value.cast::<PyDict>() {
                    for (k, v) in dict.iter() {
                        handle(k, v);
                    }
                } else {
                    let mapping_abc = get_mapping_abc(py)
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    if !value.is_instance(mapping_abc).unwrap_or(false) {
                        return Err(SerializationError::Single(
                            intern!(py, "Expected a dict").clone().unbind(),
                        ));
                    }
                    let iter = value
                        .try_iter()
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    for k_result in iter {
                        let k =
                            k_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                        let v = value
                            .get_item(&k)
                            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                        handle(k, v);
                    }
                }

                if let Some(errors) = errors {
                    return Err(SerializationError::Dict(errors.unbind()));
                }

                Ok(result.into_any().unbind())
            }
            Self::Optional { inner } => {
                if value.is_none() {
                    Ok(py.None())
                } else {
                    inner.load_from_py(py, registry, value)
                }
            }
            Self::Set { item } | Self::FrozenSet { item } | Self::Tuple { item } => {
                let invalid_err = match self {
                    Self::Set { .. } => intern!(py, "Not a valid set."),
                    Self::FrozenSet { .. } => intern!(py, "Not a valid frozenset."),
                    _ => intern!(py, "Not a valid tuple."),
                };
                if value.is_instance_of::<PyString>() {
                    return Err(SerializationError::Single(invalid_err.clone().unbind()));
                }
                let expected_err = match self {
                    Self::Set { .. } => intern!(py, "Expected a set"),
                    Self::FrozenSet { .. } => intern!(py, "Expected a frozenset"),
                    _ => intern!(py, "Expected a tuple"),
                };
                let iter = value
                    .try_iter()
                    .map_err(|_| SerializationError::Single(expected_err.clone().unbind()))?;
                let (size_hint, _) = iter.size_hint();
                let mut items = Vec::with_capacity(size_hint);
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (idx, item_result) in iter.enumerate() {
                    let v =
                        item_result.map_err(|e| SerializationError::simple(py, &e.to_string()))?;
                    match item.load_from_py(py, registry, &v) {
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
                    match variant.load_from_py(py, registry, value) {
                        Ok(result) => return Ok(result),
                        Err(e) => errors.push(e),
                    }
                }
                Err(SerializationError::collect_list(py, errors))
            }
        }
    }
}
