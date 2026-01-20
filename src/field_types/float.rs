use pyo3::prelude::*;
use pyo3::types::{PyBool, PyFloat, PyInt, PyString};
use serde_json::Value;

use super::helpers::{field_error, json_field_error, FLOAT_ERROR, FLOAT_NAN_ERROR};
use crate::types::SerializeContext;

pub mod float_serializer {
    use super::*;

    #[inline]
    pub fn serialize_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &SerializeContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if !value.is_instance_of::<PyFloat>() && !(value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>()) {
            return Err(field_error(ctx.py, field_name, FLOAT_ERROR));
        }
        if value.is_instance_of::<PyFloat>() {
            let f: f64 = value.extract()?;
            if f.is_nan() || f.is_infinite() {
                return Err(field_error(ctx.py, field_name, FLOAT_NAN_ERROR));
            }
        }
        Ok(value.clone().unbind())
    }

    #[inline]
    pub fn serialize_to_json(
        value: &Bound<'_, PyAny>,
        field_name: &str,
    ) -> Result<Value, String> {
        if !value.is_instance_of::<PyFloat>() && !(value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>()) {
            return Err(json_field_error(field_name, FLOAT_ERROR));
        }
        if value.is_instance_of::<PyInt>() {
            if let Ok(i) = value.extract::<i64>() {
                return Ok(Value::Number(serde_json::Number::from(i)));
            }
            if let Ok(u) = value.extract::<u64>() {
                return Ok(Value::Number(serde_json::Number::from(u)));
            }
            let s: String = value.str().map_err(|e: PyErr| e.to_string())?.extract().map_err(|e: PyErr| e.to_string())?;
            return Ok(Value::Number(serde_json::Number::from_string_unchecked(s)));
        }
        let f: f64 = value.extract().map_err(|e: PyErr| e.to_string())?;
        if f.is_nan() || f.is_infinite() {
            return Err(json_field_error(field_name, FLOAT_NAN_ERROR));
        }
        Ok(Value::Number(serde_json::Number::from_f64(f).expect("valid f64")))
    }

    #[inline]
    pub fn serialize<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        use serde::Serialize;
        if !value.is_instance_of::<PyFloat>() && !(value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>()) {
            return Err(S::Error::custom(json_field_error(field_name, FLOAT_ERROR)));
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
            let num = serde_json::Number::from_string_unchecked(s);
            return num.serialize(serializer);
        }
        let f: f64 = value.extract().map_err(|e: PyErr| S::Error::custom(e.to_string()))?;
        if f.is_nan() || f.is_infinite() {
            return Err(S::Error::custom(json_field_error(field_name, FLOAT_NAN_ERROR)));
        }
        serializer.serialize_f64(f)
    }
}

pub mod float_deserializer {
    use super::*;
    use crate::types::LoadContext;
    use pyo3::conversion::IntoPyObjectExt;
    use serde::de;

    #[inline]
    pub fn deserialize_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'_, 'py>,
    ) -> PyResult<Py<PyAny>> {
        if value.is_instance_of::<PyFloat>() {
            let f: f64 = value.extract()?;
            if f.is_nan() || f.is_infinite() {
                return Err(field_error(ctx.py, field_name, FLOAT_NAN_ERROR));
            }
            Ok(value.clone().unbind())
        } else if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
            Ok(value.clone().unbind())
        } else if let Ok(s) = value.cast::<PyString>() {
            let s_str = s.to_str()?;
            let f: f64 = s_str.parse().map_err(|_| field_error(ctx.py, field_name, invalid_error.unwrap_or(FLOAT_ERROR)))?;
            if f.is_nan() || f.is_infinite() {
                return Err(field_error(ctx.py, field_name, FLOAT_NAN_ERROR));
            }
            Ok(PyFloat::new(ctx.py, f).into_any().unbind())
        } else {
            Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(FLOAT_ERROR)))
        }
    }

    #[inline]
    pub fn deserialize_from_f64<E: de::Error>(py: Python, v: f64) -> Result<Py<PyAny>, E> {
        v.into_py_any(py).map_err(de::Error::custom)
    }

    #[inline]
    pub fn deserialize_from_i64<E: de::Error>(py: Python, v: i64) -> Result<Py<PyAny>, E> {
        v.into_py_any(py).map_err(de::Error::custom)
    }

    #[inline]
    pub fn deserialize_from_str<E: de::Error>(
        py: Python,
        s: &str,
        err_msg: &str,
        nan_err: &str,
    ) -> Result<Py<PyAny>, E> {
        let f: f64 = s.parse().map_err(|_| de::Error::custom(err_msg))?;
        if f.is_nan() || f.is_infinite() {
            return Err(de::Error::custom(nan_err));
        }
        f.into_py_any(py).map_err(de::Error::custom)
    }
}
