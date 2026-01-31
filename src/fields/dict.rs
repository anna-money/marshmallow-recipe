use super::helpers::{field_error, json_field_error, DICT_ERROR};
use crate::types::DumpContext;
use crate::utils::{call_validator, pyany_to_json_value, wrap_err_dict};

pub mod dict_dumper {
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyString};
    use serde_json::Value;

    use super::{call_validator, field_error, json_field_error, pyany_to_json_value, wrap_err_dict, DumpContext, DICT_ERROR};
    use crate::dumper::Dumper;

    #[inline]
    pub fn can_dump<'py>(
        value: &Bound<'py, PyAny>,
        ctx: &DumpContext<'_, 'py>,
        value_dumper: &Dumper,
    ) -> bool {
        let Ok(dict) = value.cast::<PyDict>() else {
            return false;
        };
        for (_, v) in dict.iter() {
            if !v.is_none() && !value_dumper.can_dump(&v, ctx) {
                return false;
            }
        }
        true
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        value_dumper: &Dumper,
        value_validator: Option<&Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDict>() {
            return Err(field_error(ctx.py, field_name, DICT_ERROR));
        }
        let dict = value.cast::<PyDict>()?;
        let result = PyDict::new(ctx.py);
        let mut value_errors: Option<Py<PyAny>> = None;

        for (k, v) in dict.iter() {
            if let Some(validator) = value_validator {
                if let Some(err) = call_validator(ctx.py, validator, &v)? {
                    let err_dict = value_errors.get_or_insert_with(|| PyDict::new(ctx.py).into_any().unbind());
                    err_dict.bind(ctx.py).cast::<PyDict>()?.set_item(&k, err)?;
                }
            }
            let key_str = k.cast::<PyString>()?.to_str()?;
            let dumped = dump_item(value_dumper, &v, key_str, ctx)?;
            result.set_item(k, dumped)?;
        }

        if let Some(ref errs) = value_errors {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                wrap_err_dict(ctx.py, field_name, errs.clone_ref(ctx.py)),
            ));
        }

        Ok(result.into_any().unbind())
    }

    fn dump_item<'py>(
        value_dumper: &Dumper,
        value: &Bound<'py, PyAny>,
        key: &str,
        ctx: &DumpContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if value.is_none() {
            return Ok(ctx.py.None());
        }
        value_dumper.dump_to_dict(value, key, ctx)
    }

    struct ValueDumper<'a, 'py> {
        value: &'a Bound<'py, PyAny>,
        inner: &'a Dumper,
        key: &'a str,
        ctx: &'a DumpContext<'a, 'py>,
    }

    impl serde::Serialize for ValueDumper<'_, '_> {
        fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
            if self.value.is_none() {
                return serializer.serialize_none();
            }
            self.inner.dump(self.value, self.key, self.ctx, serializer)
        }
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, '_>,
        value_dumper: &Dumper,
        value_validator: Option<&Py<PyAny>>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::{Error, SerializeMap};

        if !value.is_instance_of::<PyDict>() {
            return Err(S::Error::custom(json_field_error(field_name, DICT_ERROR)));
        }
        let dict = value.cast::<PyDict>().map_err(|e| S::Error::custom(e.to_string()))?;

        if let Some(validator) = value_validator {
            for (k, v) in dict.iter() {
                let key = k.cast::<PyString>().map_err(|e| S::Error::custom(e.to_string()))?
                    .to_str().map_err(|e| S::Error::custom(e.to_string()))?;
                if let Some(errors) = call_validator(ctx.py, validator, &v).map_err(|e| S::Error::custom(e.to_string()))? {
                    let errors_json = pyany_to_json_value(errors.bind(ctx.py));
                    let mut inner_map = serde_json::Map::new();
                    inner_map.insert(key.to_string(), errors_json);
                    let mut map = serde_json::Map::new();
                    map.insert(field_name.to_string(), Value::Object(inner_map));
                    return Err(S::Error::custom(Value::Object(map).to_string()));
                }
            }
        }

        let mut map = serializer.serialize_map(Some(dict.len()))?;
        for (k, v) in dict.iter() {
            let key = k.cast::<PyString>().map_err(|e| S::Error::custom(e.to_string()))?
                .to_str().map_err(|e| S::Error::custom(e.to_string()))?;
            map.serialize_entry(key, &ValueDumper {
                value: &v,
                inner: value_dumper,
                key,
                ctx,
            })?;
        }
        map.end()
    }
}

pub mod dict_loader {
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyString};

    use super::{call_validator, field_error, wrap_err_dict, DICT_ERROR};
    use crate::loader::Loader;
    use crate::types::LoadContext;
    use crate::utils::extract_error_value;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
        value_loader: &Loader,
        value_validator: Option<&Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyDict>() {
            return Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(DICT_ERROR)));
        }
        let dict = value.cast::<PyDict>()?;
        let result = PyDict::new(ctx.py);

        for (k, v) in dict.iter() {
            let key_str = k.cast::<PyString>()?.to_str()?;
            let val = if v.is_none() {
                ctx.py.None()
            } else {
                match value_loader.load_from_dict(&v, "value", None, ctx) {
                    Ok(val) => val,
                    Err(e) => {
                        let inner = extract_error_value(ctx.py, &e);
                        let wrapped = wrap_err_dict(ctx.py, key_str, inner);
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            wrap_err_dict(ctx.py, field_name, wrapped),
                        ));
                    }
                }
            };
            if let Some(validator) = value_validator {
                if let Some(errors) = call_validator(ctx.py, validator, val.bind(ctx.py))? {
                    let wrapped_inner = wrap_err_dict(ctx.py, "value", errors);
                    let wrapped = wrap_err_dict(ctx.py, key_str, wrapped_inner);
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        wrap_err_dict(ctx.py, field_name, wrapped),
                    ));
                }
            }
            result.set_item(k, val)?;
        }
        Ok(result.into_any().unbind())
    }
}
