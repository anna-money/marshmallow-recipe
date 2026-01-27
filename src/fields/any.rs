use super::helpers::{field_error, json_field_error, ANY_ERROR};

pub mod any_dumper {
    use pyo3::prelude::*;
    use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};
    use serde::ser::{SerializeMap, SerializeSeq};

    use super::{field_error, json_field_error, ANY_ERROR};

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        can_dump_any(value)
    }

    fn can_dump_any(value: &Bound<'_, PyAny>) -> bool {
        if value.is_none() {
            return true;
        }
        if value.is_instance_of::<PyBool>()
            || value.is_instance_of::<PyInt>()
            || value.is_instance_of::<PyString>()
        {
            return true;
        }
        if value.is_instance_of::<PyFloat>() {
            if let Ok(f) = value.extract::<f64>() {
                return !f.is_nan() && !f.is_infinite();
            }
            return false;
        }
        if let Ok(list) = value.cast::<PyList>() {
            return list.iter().all(|item| can_dump_any(&item));
        }
        if let Ok(dict) = value.cast::<PyDict>() {
            return dict.iter().all(|(k, v)| k.is_instance_of::<PyString>() && can_dump_any(&v));
        }
        false
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        py: Python<'py>,
        value: &Bound<'py, PyAny>,
        field_name: &str,
    ) -> PyResult<Py<PyAny>> {
        if value.is_none() {
            return Ok(py.None());
        }

        let is_primitive = value.is_instance_of::<PyBool>()
            || value.is_instance_of::<PyInt>()
            || value.is_instance_of::<PyFloat>()
            || value.is_instance_of::<PyString>();

        if is_primitive {
            return Ok(value.clone().unbind());
        }

        if let Ok(list) = value.cast::<PyList>() {
            let result = PyList::empty(py);
            for item in list.iter() {
                result.append(dump_to_dict(py, &item, field_name)?)?;
            }
            return Ok(result.into_any().unbind());
        }

        if let Ok(dict) = value.cast::<PyDict>() {
            let result = PyDict::new(py);
            for (k, v) in dict.iter() {
                if !k.is_instance_of::<PyString>() {
                    return Err(field_error(py, field_name, ANY_ERROR));
                }
                result.set_item(k, dump_to_dict(py, &v, field_name)?)?;
            }
            return Ok(result.into_any().unbind());
        }

        Err(field_error(py, field_name, ANY_ERROR))
    }

    struct AnyDumper<'a, 'py> {
        value: &'a Bound<'py, PyAny>,
        field_name: &'a str,
    }

    impl serde::Serialize for AnyDumper<'_, '_> {
        fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
            dump_any(self.value, self.field_name, serializer)
        }
    }

    fn dump_any<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;

        if value.is_none() {
            return serializer.serialize_none();
        }
        if value.is_instance_of::<PyBool>() {
            let b: bool = value.extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
            return serializer.serialize_bool(b);
        }
        if value.is_instance_of::<PyInt>() {
            if let Ok(i) = value.extract::<i64>() {
                return serializer.serialize_i64(i);
            }
            if let Ok(u) = value.extract::<u64>() {
                return serializer.serialize_u64(u);
            }
            let s: String = value.str().map_err(|e| S::Error::custom(e.to_string()))?
                .extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
            return serializer.serialize_str(&s);
        }
        if value.is_instance_of::<PyFloat>() {
            let f: f64 = value.extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
            if f.is_nan() || f.is_infinite() {
                return Err(S::Error::custom(json_field_error(field_name, ANY_ERROR)));
            }
            return serializer.serialize_f64(f);
        }
        if let Ok(py_str) = value.cast::<PyString>() {
            let s = py_str.to_str().map_err(|e| S::Error::custom(e.to_string()))?;
            return serializer.serialize_str(s);
        }
        if let Ok(list) = value.cast::<PyList>() {
            let mut seq = serializer.serialize_seq(Some(list.len()))?;
            for item in list.iter() {
                seq.serialize_element(&AnyDumper { value: &item, field_name })?;
            }
            return seq.end();
        }
        if let Ok(dict) = value.cast::<PyDict>() {
            let mut map = serializer.serialize_map(Some(dict.len()))?;
            for (k, v) in dict.iter() {
                let key = k.cast::<PyString>().map_err(|_| S::Error::custom(json_field_error(field_name, ANY_ERROR)))?
                    .to_str().map_err(|e| S::Error::custom(e.to_string()))?;
                map.serialize_entry(key, &AnyDumper { value: &v, field_name })?;
            }
            return map.end();
        }
        Err(S::Error::custom(json_field_error(field_name, ANY_ERROR)))
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        dump_any(value, field_name, serializer)
    }
}

pub mod any_loader {
    use pyo3::prelude::*;

    use crate::types::LoadContext;

    #[inline]
    #[allow(clippy::unnecessary_wraps)]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        _ctx: &LoadContext<'py>,
    ) -> PyResult<Py<PyAny>> {
        Ok(value.clone().unbind())
    }
}
