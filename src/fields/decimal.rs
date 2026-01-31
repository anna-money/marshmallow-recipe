use std::fmt::Write;

use arrayvec::ArrayString;
use rust_decimal::Decimal;

use super::helpers::{field_error, json_field_error, DECIMAL_ERROR, DECIMAL_NUMBER_ERROR};
use crate::cache::get_cached_types;
use crate::types::{DecimalPlaces, DumpContext};

pub type DecimalBuf = ArrayString<31>;

#[inline]
pub fn format_decimal(buf: &mut DecimalBuf, d: &Decimal) {
    write!(buf, "{d}").expect("Decimal max 31 chars: 29 digits + sign + point");
}

pub mod decimal_dumper {
    use pyo3::intern;
    use pyo3::prelude::*;
    use pyo3::types::PyString;
    use rust_decimal::Decimal;
    use rust_decimal::RoundingStrategy;
    use rust_decimal::prelude::FromStr;

    use super::{
        field_error, get_cached_types, json_field_error, DecimalPlaces,
        DumpContext, DECIMAL_ERROR, DECIMAL_NUMBER_ERROR,
    };

    #[inline]
    pub fn can_dump<'py>(value: &Bound<'py, PyAny>, ctx: &DumpContext<'_, 'py>) -> bool {
        let Ok(cached) = get_cached_types(ctx.py) else {
            return false;
        };
        value.is_instance(cached.decimal_cls.bind(ctx.py)).unwrap_or(false)
    }

    #[inline]
    pub fn dump_to_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, 'py>,
        decimal_places: DecimalPlaces,
        rounding_strategy: Option<RoundingStrategy>,
        invalid_error: Option<&str>,
    ) -> PyResult<Py<PyAny>> {
        let cached = get_cached_types(ctx.py)?;
        if !value.is_instance(cached.decimal_cls.bind(ctx.py))? {
            return Err(field_error(ctx.py, field_name, DECIMAL_ERROR));
        }
        let format_result = value.call_method1(intern!(ctx.py, "__format__"), ("f",))?;
        let formatted = format_result.cast::<PyString>()?;
        let decimal_str = formatted.to_str()?;

        let places = decimal_places.resolve(ctx.global_decimal_places);

        if let Some(strategy) = rounding_strategy {
            if let Some(places) = places {
                if let Ok(mut rust_decimal) = Decimal::from_str(decimal_str) {
                    rust_decimal = rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy);
                    let formatted_str = format!("{:.prec$}", rust_decimal, prec = places.cast_unsigned() as usize);
                    return Ok(PyString::new(ctx.py, &formatted_str).into_any().unbind());
                }
            }
        } else if let Some(places) = places {
            if let Ok(rust_decimal) = Decimal::from_str(decimal_str) {
                let normalized = rust_decimal.normalize();
                if normalized.scale() > places.cast_unsigned() {
                    let msg = invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR);
                    return Err(field_error(ctx.py, field_name, msg));
                }
            }
        }

        Ok(PyString::new(ctx.py, decimal_str).into_any().unbind())
    }

    #[inline]
    pub fn dump<S: serde::Serializer>(
        value: &Bound<'_, PyAny>,
        field_name: &str,
        ctx: &DumpContext<'_, '_>,
        decimal_places: DecimalPlaces,
        rounding_strategy: Option<RoundingStrategy>,
        invalid_error: Option<&str>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        use serde::ser::Error;
        let cached = get_cached_types(ctx.py).map_err(|e| S::Error::custom(e.to_string()))?;
        if !value.is_instance(cached.decimal_cls.bind(ctx.py)).map_err(|e| S::Error::custom(e.to_string()))? {
            return Err(S::Error::custom(json_field_error(field_name, DECIMAL_ERROR)));
        }
        let format_result = value.call_method1(intern!(ctx.py, "__format__"), ("f",)).map_err(|e| S::Error::custom(e.to_string()))?;
        let formatted = format_result.cast::<PyString>().map_err(|e| S::Error::custom(e.to_string()))?;
        let decimal_str = formatted.to_str().map_err(|e| S::Error::custom(e.to_string()))?;

        let places = decimal_places.resolve(ctx.global_decimal_places);

        if let Some(strategy) = rounding_strategy {
            if let Some(places) = places {
                if let Ok(mut rust_decimal) = Decimal::from_str(decimal_str) {
                    rust_decimal = rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy);
                    let formatted_str = format!("{:.prec$}", rust_decimal, prec = places.cast_unsigned() as usize);
                    return serializer.serialize_str(&formatted_str);
                }
            }
        } else if let Some(places) = places {
            if let Ok(rust_decimal) = Decimal::from_str(decimal_str) {
                let normalized = rust_decimal.normalize();
                if normalized.scale() > places.cast_unsigned() {
                    let msg = invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR);
                    return Err(S::Error::custom(json_field_error(field_name, msg)));
                }
            }
        }

        serializer.serialize_str(decimal_str)
    }
}

pub mod decimal_loader {
    use pyo3::prelude::*;
    use pyo3::types::{PyBool, PyFloat, PyInt, PyString};
    use rust_decimal::Decimal;
    use rust_decimal::RoundingStrategy;
    use rust_decimal::prelude::FromStr;
    use serde::de;

    use super::{field_error, format_decimal, get_cached_types, DecimalBuf, DecimalPlaces, DECIMAL_NUMBER_ERROR};
    use crate::types::LoadContext;

    #[inline]
    pub fn load_from_dict<'py>(
        value: &Bound<'py, PyAny>,
        field_name: &str,
        invalid_error: Option<&str>,
        ctx: &LoadContext<'py>,
        decimal_places: DecimalPlaces,
        rounding_strategy: Option<RoundingStrategy>,
    ) -> PyResult<Py<PyAny>> {
        let cached = get_cached_types(ctx.py)?;
        let decimal_cls = cached.decimal_cls.bind(ctx.py);
        let number_err = || field_error(ctx.py, field_name, invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR));

        let rust_decimal = if let Ok(s) = value.cast::<PyString>() {
            let s_str = s.to_str()?;
            Decimal::from_str(s_str)
                .or_else(|_| Decimal::from_scientific(s_str))
                .map_err(|_| number_err())?
        } else if value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
            if let Ok(i) = value.extract::<i64>() {
                Decimal::from(i)
            } else if let Ok(u) = value.extract::<u64>() {
                Decimal::from(u)
            } else {
                let s: String = value.str()?.extract()?;
                Decimal::from_str(&s).map_err(|_| number_err())?
            }
        } else if value.is_instance_of::<PyFloat>() {
            let f: f64 = value.extract()?;
            Decimal::try_from(f).map_err(|_| number_err())?
        } else {
            return Err(number_err());
        };

        let places = decimal_places.resolve(ctx.decimal_places);
        let final_decimal = if let Some(places) = places {
            if let Some(strategy) = rounding_strategy {
                rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy)
            } else {
                let normalized = rust_decimal.normalize();
                if normalized.scale() > places.cast_unsigned() {
                    return Err(field_error(ctx.py, field_name, invalid_error.unwrap_or(DECIMAL_NUMBER_ERROR)));
                }
                rust_decimal
            }
        } else {
            rust_decimal
        };

        let mut buf = DecimalBuf::new();
        format_decimal(&mut buf, &final_decimal);
        let result = decimal_cls.call1((buf.as_str(),))?;
        Ok(result.unbind())
    }

    #[inline]
    pub fn load_from_str<E: de::Error>(
        py: Python,
        s: &str,
        decimal_places: DecimalPlaces,
        rounding_strategy: Option<RoundingStrategy>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let rust_decimal = Decimal::from_str(s)
            .or_else(|_| Decimal::from_scientific(s))
            .map_err(|_| de::Error::custom(err_msg))?;

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = if let Some(places) = places {
            if let Some(strategy) = rounding_strategy {
                rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy)
            } else {
                let normalized = rust_decimal.normalize();
                if normalized.scale() > places.cast_unsigned() {
                    return Err(de::Error::custom(err_msg));
                }
                rust_decimal
            }
        } else {
            rust_decimal
        };

        let mut buf = DecimalBuf::new();
        format_decimal(&mut buf, &final_decimal);
        let cached = get_cached_types(py).map_err(de::Error::custom)?;
        cached.decimal_cls.bind(py).call1((buf.as_str(),))
            .map(pyo3::Bound::unbind)
            .map_err(de::Error::custom)
    }

    #[inline]
    pub fn load_from_i64<E: de::Error>(
        py: Python,
        v: i64,
        decimal_places: DecimalPlaces,
        rounding_strategy: Option<RoundingStrategy>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let rust_decimal = Decimal::from(v);

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = if let Some(places) = places {
            if let Some(strategy) = rounding_strategy {
                rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy)
            } else {
                let normalized = rust_decimal.normalize();
                if normalized.scale() > places.cast_unsigned() {
                    return Err(de::Error::custom(err_msg));
                }
                rust_decimal
            }
        } else {
            rust_decimal
        };

        let mut buf = DecimalBuf::new();
        format_decimal(&mut buf, &final_decimal);
        let cached = get_cached_types(py).map_err(de::Error::custom)?;
        cached.decimal_cls.bind(py).call1((buf.as_str(),))
            .map(pyo3::Bound::unbind)
            .map_err(de::Error::custom)
    }

    #[inline]
    pub fn load_from_u64<E: de::Error>(
        py: Python,
        v: u64,
        decimal_places: DecimalPlaces,
        rounding_strategy: Option<RoundingStrategy>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let rust_decimal = Decimal::from(v);

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = if let Some(places) = places {
            if let Some(strategy) = rounding_strategy {
                rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy)
            } else {
                let normalized = rust_decimal.normalize();
                if normalized.scale() > places.cast_unsigned() {
                    return Err(de::Error::custom(err_msg));
                }
                rust_decimal
            }
        } else {
            rust_decimal
        };

        let mut buf = DecimalBuf::new();
        format_decimal(&mut buf, &final_decimal);
        let cached = get_cached_types(py).map_err(de::Error::custom)?;
        cached.decimal_cls.bind(py).call1((buf.as_str(),))
            .map(pyo3::Bound::unbind)
            .map_err(de::Error::custom)
    }

    #[inline]
    pub fn load_from_f64<E: de::Error>(
        py: Python,
        v: f64,
        decimal_places: DecimalPlaces,
        rounding_strategy: Option<RoundingStrategy>,
        ctx_decimal_places: Option<i32>,
        err_msg: &str,
    ) -> Result<Py<PyAny>, E> {
        let rust_decimal = Decimal::try_from(v).map_err(|_| de::Error::custom(err_msg))?;

        let places = decimal_places.resolve(ctx_decimal_places);
        let final_decimal = if let Some(places) = places {
            if let Some(strategy) = rounding_strategy {
                rust_decimal.round_dp_with_strategy(places.cast_unsigned(), strategy)
            } else {
                let normalized = rust_decimal.normalize();
                if normalized.scale() > places.cast_unsigned() {
                    return Err(de::Error::custom(err_msg));
                }
                rust_decimal
            }
        } else {
            rust_decimal
        };

        let mut buf = DecimalBuf::new();
        format_decimal(&mut buf, &final_decimal);
        let cached = get_cached_types(py).map_err(de::Error::custom)?;
        cached.decimal_cls.bind(py).call1((buf.as_str(),))
            .map(pyo3::Bound::unbind)
            .map_err(de::Error::custom)
    }
}
