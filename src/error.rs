use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyDict, PyList, PyString};

pub enum SerializationError {
    Single(Py<PyString>),
    List(Py<PyList>),
    Dict(Py<PyDict>),
}

pub type DumpError = SerializationError;
pub type LoadError = SerializationError;

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
