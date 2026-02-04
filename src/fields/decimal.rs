use pyo3::conversion::IntoPyObjectExt;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyString, PyType};

use crate::error::{DumpError, LoadError};

const DECIMAL_ERROR: &str = "Not a valid decimal.";
const DECIMAL_NUMBER_ERROR: &str = "Not a valid number.";

pub fn get_decimal_cls(py: Python<'_>) -> PyResult<&Bound<'_, PyType>> {
    static DECIMAL_CLS: PyOnceLock<Py<PyType>> = PyOnceLock::new();
    DECIMAL_CLS.import(py, "decimal", "Decimal")
}

pub fn get_quantize_exp(py: Python<'_>, places: u32) -> PyResult<Bound<'_, PyAny>> {
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
    let py = value.py();
    let normalized = value.call_method0(intern!(py, "normalize"))?;
    let as_tuple = normalized.call_method0(intern!(py, "as_tuple"))?;
    let exponent: i32 = as_tuple.getattr(intern!(py, "exponent"))?.extract()?;
    Ok(if exponent < 0 {
        (-exponent).cast_unsigned()
    } else {
        0
    })
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

pub fn load(
    py: Python<'_>,
    value: &serde_json::Value,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR);

    if let Some(s) = value.as_str() {
        return decimal_loader::load_from_str::<serde::de::value::Error>(
            py,
            s,
            decimal_places,
            rounding,
            err_msg,
        )
        .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(i) = value.as_i64() {
        return decimal_loader::load_from_i64::<serde::de::value::Error>(
            py,
            i,
            decimal_places,
            rounding,
            err_msg,
        )
        .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(u) = value.as_u64() {
        return decimal_loader::load_from_u64::<serde::de::value::Error>(
            py,
            u,
            decimal_places,
            rounding,
            err_msg,
        )
        .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(n) = value.as_number() {
        let s = n.to_string();
        return decimal_loader::load_from_str::<serde::de::value::Error>(
            py,
            &s,
            decimal_places,
            rounding,
            err_msg,
        )
        .map_err(|e| LoadError::simple(&e.to_string()));
    }
    if let Some(f) = value.as_f64() {
        return decimal_loader::load_from_f64::<serde::de::value::Error>(
            py,
            f,
            decimal_places,
            rounding,
            err_msg,
        )
        .map_err(|e| LoadError::simple(&e.to_string()));
    }

    Err(LoadError::simple(err_msg))
}

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
    invalid_error: Option<&str>,
) -> Result<Py<PyAny>, LoadError> {
    let err_msg = invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR);
    let py = value.py();

    let s: String = value
        .str()
        .map_err(|_| LoadError::simple(err_msg))?
        .extract()
        .map_err(|_: PyErr| LoadError::simple(err_msg))?;

    decimal_loader::load_from_str::<serde::de::value::Error>(
        py,
        &s,
        decimal_places,
        rounding,
        err_msg,
    )
    .map_err(|e| LoadError::simple(&e.to_string()))
}


pub fn dump(
    value: &Bound<'_, PyAny>,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
) -> Result<serde_json::Value, DumpError> {
    let py = value.py();

    let decimal = if let Some(places) = decimal_places {
        if let Some(rounding) = rounding {
            let exp = get_quantize_exp(py, places.unsigned_abs())
                .map_err(|e| DumpError::simple(&e.to_string()))?;
            value
                .call_method1(intern!(py, "quantize"), (&exp, rounding.bind(py)))
                .map_err(|e| DumpError::simple(&e.to_string()))?
        } else {
            let scale = get_decimal_scale(value).map_err(|e| DumpError::simple(&e.to_string()))?;
            if scale > places.unsigned_abs() {
                return Err(DumpError::simple(DECIMAL_NUMBER_ERROR));
            }
            value.clone()
        }
    } else {
        value.clone()
    };

    let formatted = decimal
        .call_method1(intern!(py, "__format__"), ("f",))
        .map_err(|e| DumpError::simple(&e.to_string()))?;

    let s: &str = formatted
        .cast::<PyString>()
        .map_err(|_| DumpError::simple(DECIMAL_ERROR))?
        .to_str()
        .map_err(|e| DumpError::simple(&e.to_string()))?;

    Ok(serde_json::Value::String(s.to_string()))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
) -> Result<Py<PyAny>, DumpError> {
    let py = value.py();

    let decimal = if let Some(places) = decimal_places {
        if let Some(rounding) = rounding {
            let exp = get_quantize_exp(py, places.unsigned_abs())
                .map_err(|e| DumpError::simple(&e.to_string()))?;
            value
                .call_method1(intern!(py, "quantize"), (&exp, rounding.bind(py)))
                .map_err(|e| DumpError::simple(&e.to_string()))?
        } else {
            let scale = get_decimal_scale(value).map_err(|e| DumpError::simple(&e.to_string()))?;
            if scale > places.unsigned_abs() {
                return Err(DumpError::simple(DECIMAL_NUMBER_ERROR));
            }
            value.clone()
        }
    } else {
        value.clone()
    };

    let formatted = decimal
        .call_method1(intern!(py, "__format__"), ("f",))
        .map_err(|e| DumpError::simple(&e.to_string()))?;

    let s: &str = formatted
        .cast::<PyString>()
        .map_err(|_| DumpError::simple(DECIMAL_ERROR))?
        .to_str()
        .map_err(|e| DumpError::simple(&e.to_string()))?;

    s.into_py_any(py)
        .map_err(|e| DumpError::simple(&e.to_string()))
}

pub mod decimal_loader {
    use pyo3::prelude::*;
    use serde::de;

    use super::{apply_rounding_or_validate, get_decimal_cls};

    #[inline]
    pub fn load_from_str<E: de::Error>(
        py: Python,
        s: &str,
        decimal_places: Option<i32>,
        rounding: Option<&Py<PyAny>>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let py_decimal = decimal_cls
            .call1((s,))
            .map_err(|_| de::Error::custom(err_msg))?;

        let final_decimal = apply_rounding_or_validate(&py_decimal, decimal_places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }

    #[inline]
    pub fn load_from_i64<E: de::Error>(
        py: Python,
        v: i64,
        decimal_places: Option<i32>,
        rounding: Option<&Py<PyAny>>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let py_decimal = decimal_cls.call1((v,)).map_err(de::Error::custom)?;

        let final_decimal = apply_rounding_or_validate(&py_decimal, decimal_places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }

    #[inline]
    pub fn load_from_u64<E: de::Error>(
        py: Python,
        v: u64,
        decimal_places: Option<i32>,
        rounding: Option<&Py<PyAny>>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let py_decimal = decimal_cls.call1((v,)).map_err(de::Error::custom)?;

        let final_decimal = apply_rounding_or_validate(&py_decimal, decimal_places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }

    #[inline]
    pub fn load_from_f64<E: de::Error>(
        py: Python,
        v: f64,
        decimal_places: Option<i32>,
        rounding: Option<&Py<PyAny>>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let decimal_cls = get_decimal_cls(py).map_err(de::Error::custom)?;
        let v_str = v.to_string();
        let py_decimal = decimal_cls
            .call1((&v_str,))
            .map_err(|_| de::Error::custom(err_msg))?;

        let final_decimal = apply_rounding_or_validate(&py_decimal, decimal_places, rounding)
            .map_err(|_| de::Error::custom(err_msg))?;

        Ok(final_decimal.unbind())
    }
}
