use pyo3::intern;
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyBool, PyFloat, PyInt, PyString, PyType};

use crate::error::SerializationError;

pub struct RangeBound {
    pub value: Py<PyAny>,
    pub error: Py<PyString>,
}

impl Clone for RangeBound {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            value: self.value.clone_ref(py),
            error: self.error.clone_ref(py),
        })
    }
}

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

#[allow(clippy::too_many_arguments)]
pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if value.is_instance_of::<PyBool>() {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let decimal_cls =
        get_decimal_cls(py).map_err(|e| SerializationError::simple(py, &e.to_string()))?;

    if value.is_instance_of::<PyInt>() {
        let py_decimal = decimal_cls
            .call1((value,))
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let result = finalize_decimal(&py_decimal, decimal_places, rounding, invalid_error)?;
        validate_range(result.bind(py), gt, gte, lt, lte)?;
        return Ok(result);
    }

    if value.is_instance_of::<PyString>() {
        let py_decimal = decimal_cls
            .call1((value,))
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let is_finite: bool = py_decimal
            .call_method0(intern!(py, "is_finite"))
            .and_then(|v| v.extract())
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !is_finite {
            return Err(SerializationError::Single(invalid_error.clone_ref(py)));
        }
        let result = finalize_decimal(&py_decimal, decimal_places, rounding, invalid_error)?;
        validate_range(result.bind(py), gt, gte, lt, lte)?;
        return Ok(result);
    }

    if value.is_instance_of::<PyFloat>() {
        let f: f64 = value
            .extract()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        if !f.is_finite() {
            return Err(SerializationError::Single(invalid_error.clone_ref(py)));
        }
        let s = value
            .str()
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let py_decimal = decimal_cls
            .call1((&s,))
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        let result = finalize_decimal(&py_decimal, decimal_places, rounding, invalid_error)?;
        validate_range(result.bind(py), gt, gte, lt, lte)?;
        return Ok(result);
    }

    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

#[allow(clippy::too_many_arguments)]
pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();

    if !is_instance_of_decimal(value).map_err(|e| SerializationError::simple(py, &e.to_string()))? {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let is_finite: bool = value
        .call_method0(intern!(py, "is_finite"))
        .and_then(|v| v.extract())
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    if !is_finite {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }

    let decimal = if let Some(places) = decimal_places {
        if let Some(rounding) = rounding {
            let exp = get_quantize_exp(py, places.unsigned_abs())
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            value
                .call_method1(intern!(py, "quantize"), (&exp, rounding.bind(py)))
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?
        } else {
            let scale = get_decimal_scale(value)
                .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
            if scale > places.unsigned_abs() {
                return Err(SerializationError::Single(invalid_error.clone_ref(py)));
            }
            value.clone()
        }
    } else {
        value.clone()
    };

    validate_range(&decimal, gt, gte, lt, lte)?;

    let formatted = decimal
        .call_method1(intern!(py, "__format__"), ("f",))
        .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
    Ok(formatted.unbind())
}

fn finalize_decimal(
    py_decimal: &Bound<'_, PyAny>,
    decimal_places: Option<i32>,
    rounding: Option<&Py<PyAny>>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = py_decimal.py();
    let Some(places) = decimal_places else {
        return Ok(py_decimal.clone().unbind());
    };
    if let Some(rounding) = rounding {
        quantize_decimal(py_decimal, places.cast_unsigned(), rounding)
            .map(Bound::unbind)
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))
    } else {
        let scale = get_decimal_scale(py_decimal)
            .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)))?;
        if scale > places.cast_unsigned() {
            return Err(SerializationError::Single(invalid_error.clone_ref(py)));
        }
        Ok(py_decimal.clone().unbind())
    }
}

fn validate_range(
    value: &Bound<'_, PyAny>,
    gt: Option<&RangeBound>,
    gte: Option<&RangeBound>,
    lt: Option<&RangeBound>,
    lte: Option<&RangeBound>,
) -> Result<(), SerializationError> {
    let py = value.py();
    if let Some(bound) = gt {
        let ok = value
            .gt(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    if let Some(bound) = gte {
        let ok = value
            .ge(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    if let Some(bound) = lt {
        let ok = value
            .lt(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    if let Some(bound) = lte {
        let ok = value
            .le(bound.value.bind(py))
            .map_err(|e| SerializationError::simple(py, &e.to_string()))?;
        if !ok {
            return Err(SerializationError::Single(bound.error.clone_ref(py)));
        }
    }
    Ok(())
}

fn is_instance_of_decimal(value: &Bound<'_, PyAny>) -> PyResult<bool> {
    let py = value.py();
    let decimal_cls = get_decimal_cls(py)?;
    value.is_instance(decimal_cls)
}
