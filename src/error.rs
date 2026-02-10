use pyo3::conversion::IntoPyObject;
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyDict, PyList, PyString};

pub enum SerializationError {
    Single(Py<PyString>),
    List(Py<PyList>),
    Dict(Py<PyDict>),
}

impl SerializationError {
    pub fn simple(py: Python<'_>, msg: &str) -> Self {
        Self::Single(PyString::new(py, msg).unbind())
    }

    pub fn collect_list(py: Python<'_>, errors: Vec<Self>) -> Self {
        let items: Vec<Py<PyAny>> = errors
            .into_iter()
            .map(|e| e.to_py_value(py).unwrap_or_else(|_| py.None()))
            .collect();
        Self::List(PyList::new(py, items).expect("valid items").unbind())
    }

    pub fn to_py_value(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match self {
            Self::Single(s) => {
                let list = PyList::new(py, [s.bind(py)])?;
                Ok(list.into_any().unbind())
            }
            Self::List(l) => Ok(l.clone_ref(py).into_any()),
            Self::Dict(d) => Ok(d.clone_ref(py).into_any()),
        }
    }

    pub fn to_validation_err(&self, py: Python<'_>) -> PyErr {
        let cls = get_validation_error_cls(py);
        if let Ok(cls) = cls
            && let Ok(py_val) = self.to_py_value(py)
            && let Ok(err_instance) = cls.call1((py_val,))
        {
            return PyErr::from_value(err_instance);
        }
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("{self:?}"))
    }
}

fn get_validation_error_cls(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
    static VALIDATION_ERROR_CLS: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
    VALIDATION_ERROR_CLS
        .get_or_try_init(py, || {
            let mod_ = py.import("marshmallow")?;
            mod_.getattr("ValidationError").map(Bound::unbind)
        })
        .map(|v| v.bind(py))
}

impl std::fmt::Debug for SerializationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        Python::attach(|py| match self {
            Self::Single(s) => {
                let msg = s.bind(py).to_str().unwrap_or("<invalid>");
                write!(f, "Single({msg})")
            }
            Self::List(l) => write!(f, "List({:?})", l.bind(py)),
            Self::Dict(d) => write!(f, "Dict({:?})", d.bind(py)),
        })
    }
}

pub fn accumulate_error<'py, K: IntoPyObject<'py>>(
    py: Python<'py>,
    errors: &mut Option<Bound<'py, PyDict>>,
    key: K,
    error: &SerializationError,
) {
    let err_dict = errors.get_or_insert_with(|| PyDict::new(py));
    let _ = err_dict.set_item(key, error.to_py_value(py).unwrap_or_else(|_| py.None()));
}

pub fn pyerrors_to_serialization_error(py: Python<'_>, errors: &Py<PyAny>) -> SerializationError {
    let error = pyany_to_serialization_error(py, errors.bind(py));
    maybe_wrap_nested_error(py, error)
}

fn pyany_to_serialization_error(py: Python<'_>, value: &Bound<'_, PyAny>) -> SerializationError {
    if let Ok(s) = value.extract::<String>() {
        return SerializationError::simple(py, &s);
    }
    if let Ok(list) = value.cast::<PyList>() {
        if list.is_empty() {
            return SerializationError::List(list.clone().unbind());
        }
        let all_strings = list.iter().all(|item| item.extract::<String>().is_ok());
        if all_strings {
            return SerializationError::List(list.clone().unbind());
        }
        if list.len() == 1
            && let Ok(item) = list.get_item(0)
        {
            return pyany_to_serialization_error(py, &item);
        }
        let dict = PyDict::new(py);
        for (idx, item) in list.iter().enumerate() {
            let _ = dict.set_item(
                idx,
                pyany_to_serialization_error(py, &item)
                    .to_py_value(py)
                    .unwrap_or_else(|_| py.None()),
            );
        }
        return SerializationError::Dict(dict.unbind());
    }
    if let Ok(dict) = value.cast::<PyDict>() {
        let result = PyDict::new(py);
        for (k, v) in dict.iter() {
            let _ = result.set_item(
                &k,
                pyany_to_serialization_error(py, &v)
                    .to_py_value(py)
                    .unwrap_or_else(|_| py.None()),
            );
        }
        return SerializationError::Dict(result.unbind());
    }
    SerializationError::simple(py, &value.to_string())
}

fn maybe_wrap_nested_error(py: Python<'_>, e: SerializationError) -> SerializationError {
    match e {
        SerializationError::Dict(d) => {
            let val = d.into_any();
            SerializationError::List(
                PyList::new(py, [val.bind(py)])
                    .expect("single element")
                    .unbind(),
            )
        }
        other => other,
    }
}
