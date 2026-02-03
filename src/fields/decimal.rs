use pyo3::intern;
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::PyType;

use super::helpers::{field_error, json_field_error, DECIMAL_ERROR, DECIMAL_NUMBER_ERROR};
use crate::types::DecimalPlaces;

fn get_decimal_cls(py: Python<'_>) -> PyResult<&Bound<'_, PyType>> {
    static DECIMAL_CLS: PyOnceLock<Py<PyType>> = PyOnceLock::new();
    DECIMAL_CLS.import(py, "decimal", "Decimal")
}

fn get_quantize_exp(py: Python<'_>, places: u32) -> PyResult<Bound<'_, PyAny>> {
    const MAX_CACHED_PLACES: usize = 16;

    static QUANTIZE_EXP_CACHE: [PyOnceLock<Py<PyAny>>; MAX_CACHED_PLACES] =
        [const { PyOnceLock::new() }; MAX_CACHED_PLACES];

    let idx = places as usize;
    if idx < MAX_CACHED_PLACES {
        QUANTIZE_EXP_CACHE[idx]
            .get_or_try_init(py, || {
                let exp_str = format!("0.{}", "0".repeat(places as usize));
                get_decimal_cls(py)?.call1((&exp_str,)).map(Bound::unbind)
            })
            .map(|v| v.bind(py).clone())
    } else {
        let exp_str = format!("0.{}", "0".repeat(places as usize));
        get_decimal_cls(py)?.call1((&exp_str,))
    }
}

fn get_decimal_scale(value: &Bound<'_, PyAny>) -> PyResult<u32> {
    let normalized = value.call_method0(intern!(value.py(), "normalize"))?;
    let as_tuple = normalized.call_method0(intern!(value.py(), "as_tuple"))?;
    let exponent: i32 = as_tuple.getattr(intern!(value.py(), "exponent"))?.extract()?;
    Ok(if exponent < 0 { (-exponent).cast_unsigned() } else { 0 })
}

fn quantize_decimal<'py>(
    value: &Bound<'py, PyAny>,
    places: u32,
    rounding: &Py<PyAny>,
) -> PyResult<Bound<'py, PyAny>> {
    let py = value.py();
    let exp = get_quantize_exp(py, places)?;
    value.call_method1(intern!(py, "quantize"), (&exp, rounding.bind(py)))
}

fn apply_rounding_or_validate<'py>(
    value: &Bound<'py, PyAny>,
    places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
) -> PyResult<Bound<'py, PyAny>> {
    let Some(places) = places else {
        return Ok(value.clone());
    };

    if let Some(rounding) = rounding {
        quantize_decimal(value, places.cast_unsigned(), rounding)
    } else {
        let scale = get_decimal_scale(value)?;
        if scale > places.cast_unsigned() {
            return Err(pyo3::exceptions::PyValueError::new_err("scale exceeded"));
        }
        Ok(value.clone())
    }
}

pub mod decimal_dumper {
    use pyo3::intern;
    use pyo3::prelude::*;
    use pyo3::types::PyString;

    use super::{
        apply_rounding_or_validate, field_error, get_decimal_cls, json_field_error, DecimalPlaces,
        DECIMAL_ERROR, DECIMAL_NUMBER_ERROR,
    };

    #[inline]
    fn format_decimal_fixed_point<'py>(value: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyString>> {
        let format_result = value.call_method1(intern!(value.py(), "__format__"), ("f",))?;
        Ok(format_result.cast_into()?)
    }

    #[inline]
    pub fn can_dump(value: &Bound<'_, PyAny>) -> bool {
        let Ok(decimal_cls) = get_decimal_cls(value.py()) else {
            return false;
        };
        value.is_instance(decimal_cls).unwrap_or(false)
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &crate::types::DumpContext<'_, 'py>,
        decimal_places: DecimalPlaces,
        rounding: Option<&Py<PyAny>>,
        invalid_error: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        let decimal_cls = get_decimal_cls(ctx.py)?;
        if !value.is_instance(decimal_cls)? {
            return Err(field_error(ctx.py, field_name, DECIMAL_ERROR));
        }

        let places = decimal_places.resolve(ctx.global_decimal_places);
        let decimal = apply_rounding_or_validate(value, places, rounding)
            .map_err(|_| field_error(ctx.py, field_name, invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR)))?;
        let decimal_str = format_decimal_fixed_point(&decimal)
            .map_err(|_| field_error(ctx.py, field_name, invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR)))?;
        Ok(decimal_str.into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &crate::types::DumpContext<'_, '_>,
        decimal_places: DecimalPlaces,
        rounding: Option<&Py<PyAny>>,
        invalid_error: Option<&str>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;

        let decimal_cls = get_decimal_cls(ctx.py).map_err(|e| S::Error::custom(e.to_string()))?;
        if !value.is_instance(decimal_cls).map_err(|e| S::Error::custom(e.to_string()))? {
            return Err(S::Error::custom(json_field_error(field_name, DECIMAL_ERROR)));
        }

        let places = decimal_places.resolve(ctx.global_decimal_places);
        let decimal = apply_rounding_or_validate(value, places, rounding)
            .map_err(|_| S::Error::custom(json_field_error(field_name, invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR))))?;
        let decimal_str = format_decimal_fixed_point(&decimal)
            .map_err(|_| S::Error::custom(json_field_error(field_name, invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR))))?;
        let decimal_str_ref = decimal_str.to_str().map_err(|e| S::Error::custom(e.to_string()))?;
        serializer.serialize_str(decimal_str_ref)
    }
}

pub mod decimal_loader {
    use pyo3::prelude::*;
    use pyo3::types::{PyBool, PyFloat, PyInt, PyString};
    use serde::de;

    use super::{
        apply_rounding_or_validate, field_error, get_decimal_cls, DecimalPlaces,
        DECIMAL_NUMBER_ERROR,
    };
    use crate::types::LoadContext;

    fn create_decimal_from_value<'py>(
        py: Python<'py>,
        value: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let decimal_cls = get_decimal_cls(py)?;
        if value.is_instance_of::<PyFloat>() {
            let str_repr = value.str()?;
            decimal_cls.call1((str_repr,))
        } else {
            decimal_cls.call1((value,))
        }
    }

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
        decimal_places: DecimalPlaces,
        rounding: Option<&Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let number_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR));

        let py_decimal = if let Ok(s) = value.cast::<PyString>() {
            let decimal_cls = get_decimal_cls(ctx.py)?;
            decimal_cls.call1((s,)).map_err(|_| number_err())?
        } else if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
            create_decimal_from_value(ctx.py, value).map_err(|_| number_err())?
        } else if value.is_instance_of::<PyFloat>() {
            create_decimal_from_value(ctx.py, value).map_err(|_| number_err())?
        } else {
            return Err(number_err());
        };

        let places = decimal_places.resolve(ctx.decimal_places);
        let final_decimal = apply_rounding_or_validate(&py_decimal, places, rounding)
            .map_err(|_| number_err())?;
        Ok(final_decimal.unbind())
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(
        py: Python,
        s: &str,
        decimal_places: DecimalPlaces,
        rounding: Option<&Py<PyAny>>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let py_decimal = decimal_cls.call1((s,)).map_err(|_| de::Error::custom(err_msg))?;

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = apply_rounding_or_validate(&py_decimal, places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }

    #[inline]
    pub fn load_from_i64<E: de::Error>(
        py: Python,
        v: i64,
        decimal_places: DecimalPlaces,
        rounding: Option<&Py<PyAny>>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let py_decimal = decimal_cls.call1((v,)).map_err(de::Error::custom)?;

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = apply_rounding_or_validate(&py_decimal, places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }

    #[inline]
    pub fn load_from_u64<E: de::Error>(
        py: Python,
        v: u64,
        decimal_places: DecimalPlaces,
        rounding: Option<&Py<PyAny>>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let py_decimal = decimal_cls.call1((v,)).map_err(de::Error::custom)?;

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = apply_rounding_or_validate(&py_decimal, places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }

    #[inline]
    pub fn load_from_f64<E: de::Error>(
        py: Python,
        v: f64,
        decimal_places: DecimalPlaces,
        rounding: Option<&Py<PyAny>>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let v_str = v.to_string();
        let py_decimal = decimal_cls.call1((&v_str,)).map_err(|_| de::Error::custom(err_msg))?;

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = apply_rounding_or_validate(&py_decimal, places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }
}
