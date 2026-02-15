use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFrozenSet, PyList, PySet, PyString, PyTuple};
use smallbitvec::SmallBitVec;

use crate::container::{DataclassContainer, FieldCommon, FieldContainer, TypeContainer};
use crate::error::{SerializationError, accumulate_error, pyerrors_to_serialization_error};
use crate::fields::{
    any, bool_type, collection, date, datetime, decimal, dict, float_type, int_enum, int_type,
    str_enum, str_type, time, union, uuid,
};
use crate::slots::set_slot_value_direct;
use crate::utils::{call_validator, extract_error_args, get_object_cls, new_presized_list};

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
    pub fn load_from_py(&self, value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, SerializationError> {
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
            } => {
                let result = str_type::load_from_py(
                    value,
                    *strip_whitespaces,
                    common.optional,
                    &common.invalid_error,
                    min_length.as_ref(),
                    max_length.as_ref(),
                    regexp.as_ref(),
                )?;
                if let Some(post_load_fn) = post_load {
                    post_load_fn
                        .call1(py, (&result,))
                        .map_err(|e| SerializationError::simple(py, &e.to_string()))
                } else {
                    Ok(result)
                }
            }
            Self::Int { .. } => int_type::load_from_py(value, &common.invalid_error),
            Self::Float { .. } => float_type::load_from_py(value, &common.invalid_error),
            Self::Bool { .. } => bool_type::load_from_py(value, &common.invalid_error),
            Self::Decimal {
                decimal_places,
                rounding,
                ..
            } => decimal::load_from_py(
                value,
                *decimal_places,
                rounding.as_ref(),
                &common.invalid_error,
            ),
            Self::Date { .. } => date::load_from_py(value, &common.invalid_error),
            Self::Time { .. } => time::load_from_py(value, &common.invalid_error),
            Self::DateTime { format, .. } => {
                datetime::load_from_py(value, format, &common.invalid_error)
            }
            Self::Uuid { .. } => uuid::load_from_py(value, &common.invalid_error),
            Self::StrEnum {
                common,
                loader_data,
                ..
            } => str_enum::load_from_py(value, loader_data, &common.invalid_error),
            Self::IntEnum {
                common,
                loader_data,
                ..
            } => int_enum::load_from_py(value, loader_data, &common.invalid_error),
            Self::Any { .. } => Ok(any::load_from_py(value)),
            Self::Collection {
                kind,
                item,
                item_validator,
                ..
            } => collection::load_from_py(
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
            } => dict::load_from_py(
                value,
                value_schema,
                value_validator.as_ref(),
                &common.invalid_error,
            ),
            Self::Nested { container, .. } => container.load_from_py(value),
            Self::Union { variants, .. } => union::load_from_py(value, variants),
        }
    }
}

impl DataclassContainer {
    pub fn load_from_py(&self, value: &Bound<'_, PyAny>) -> Result<Py<PyAny>, SerializationError> {
        let py = value.py();
        let dict = value.cast::<PyDict>().map_err(|_| {
            let err_dict = PyDict::new(py);
            let _ = err_dict.set_item(
                "_schema",
                PyList::new(py, [intern!(py, NESTED_ERROR)]).unwrap(),
            );
            SerializationError::Dict(err_dict.unbind())
        })?;

        if self.can_use_direct_slots {
            self.load_from_py_direct_slots(dict)
        } else {
            self.load_from_py_kwargs(dict)
        }
    }

    fn load_from_py_kwargs(
        &self,
        dict: &Bound<'_, PyDict>,
    ) -> Result<Py<PyAny>, SerializationError> {
        let py = dict.py();
        let kwargs = PyDict::new(py);
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

                match dc_field.field.load_from_py(&v) {
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

    #[allow(clippy::too_many_lines)]
    fn load_from_py_direct_slots(
        &self,
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

                match dc_field.field.load_from_py(&v) {
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

impl TypeContainer {
    #[allow(clippy::too_many_lines)]
    pub fn load_from_py(
        &self,
        py: Python<'_>,
        value: &Bound<'_, PyAny>,
    ) -> Result<Py<PyAny>, SerializationError> {
        match self {
            Self::Dataclass(dc) => dc.load_from_py(value),
            Self::Primitive(p) => {
                if value.is_none() {
                    return Ok(py.None());
                }
                p.field.load_from_py(value)
            }
            Self::List { item } => {
                let list = value.cast::<PyList>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a list").clone().unbind())
                })?;
                let result = new_presized_list(py, list.len());
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (idx, v) in list.iter().enumerate() {
                    match item.load_from_py(py, &v) {
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
                let dict = value.cast::<PyDict>().map_err(|_| {
                    SerializationError::Single(intern!(py, "Expected a dict").clone().unbind())
                })?;
                let result = PyDict::new(py);
                let mut errors: Option<Bound<'_, PyDict>> = None;

                for (k, v) in dict.iter() {
                    let key_str = k
                        .cast::<PyString>()
                        .ok()
                        .and_then(|s| s.to_str().ok())
                        .unwrap_or("");
                    match value_container.load_from_py(py, &v) {
                        Ok(py_val) => {
                            let _ = result.set_item(k, py_val);
                        }
                        Err(ref e) => accumulate_error(py, &mut errors, key_str, e),
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
                    inner.load_from_py(py, value)
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
                    match item.load_from_py(py, &v) {
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
                    match variant.load_from_py(py, value) {
                        Ok(result) => return Ok(result),
                        Err(e) => errors.push(e),
                    }
                }
                Err(SerializationError::collect_list(py, errors))
            }
        }
    }
}
