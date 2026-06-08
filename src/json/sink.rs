use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};

use crate::error::SerializationError;
use crate::json::writer::JsonWriter;

const ANY_ERROR: &str = "Not a valid JSON-serializable value.";

/// A sink for a JSON value tree. The traversal drives the sink with leaf/null/object/array
/// events; nesting rides the Rust call stack via `open_object`/`open_array` closures (no heap
/// stack), which is what keeps the `PyDictSink` path at parity with a hand-written builder.
///
/// `key` is `Some(_)` for object members and `None` for array items and the single root value.
pub trait DumpSink<'py> {
    type Out;

    fn leaf(&mut self, key: Option<&str>, v: &Bound<'py, PyAny>) -> Result<(), SerializationError>;
    fn null(&mut self, key: Option<&str>) -> Result<(), SerializationError>;
    fn pyobject(
        &mut self,
        key: Option<&str>,
        v: &Bound<'py, PyAny>,
    ) -> Result<(), SerializationError>;
    fn open_object<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>;
    fn open_array<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>;
    fn finish(self) -> Self::Out;
}

enum Cur<'py> {
    Root,
    Dict(Bound<'py, PyDict>),
    List(Bound<'py, PyList>),
}

pub struct PyDictSink<'py> {
    py: Python<'py>,
    current: Cur<'py>,
    root: Option<Py<PyAny>>,
}

impl<'py> PyDictSink<'py> {
    pub const fn new(py: Python<'py>) -> Self {
        Self {
            py,
            current: Cur::Root,
            root: None,
        }
    }

    fn attach(
        &mut self,
        key: Option<&str>,
        v: &Bound<'py, PyAny>,
    ) -> Result<(), SerializationError> {
        match (&self.current, key) {
            (Cur::Dict(d), Some(k)) => d
                .set_item(k, v)
                .map_err(|e| SerializationError::simple(self.py, &e.to_string())),
            (Cur::List(l), None) => l
                .append(v)
                .map_err(|e| SerializationError::simple(self.py, &e.to_string())),
            (Cur::Root, None) => {
                self.root = Some(v.clone().unbind());
                Ok(())
            }
            _ => Err(SerializationError::simple(self.py, "sink misuse")),
        }
    }
}

impl<'py> DumpSink<'py> for PyDictSink<'py> {
    type Out = Py<PyAny>;

    fn leaf(&mut self, key: Option<&str>, v: &Bound<'py, PyAny>) -> Result<(), SerializationError> {
        self.attach(key, v)
    }

    fn null(&mut self, key: Option<&str>) -> Result<(), SerializationError> {
        let none = self.py.None().into_bound(self.py);
        self.attach(key, &none)
    }

    fn pyobject(
        &mut self,
        key: Option<&str>,
        v: &Bound<'py, PyAny>,
    ) -> Result<(), SerializationError> {
        self.attach(key, v)
    }

    fn open_object<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>,
    {
        let child = PyDict::new(self.py);
        let parent = std::mem::replace(&mut self.current, Cur::Dict(child.clone()));
        let r = body(self);
        self.current = parent;
        r?;
        self.attach(key, &child.into_any())
    }

    fn open_array<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>,
    {
        let child = PyList::empty(self.py);
        let parent = std::mem::replace(&mut self.current, Cur::List(child.clone()));
        let r = body(self);
        self.current = parent;
        r?;
        self.attach(key, &child.into_any())
    }

    fn finish(self) -> Self::Out {
        self.root.unwrap_or_else(|| self.py.None())
    }
}

pub struct JsonWriterSink {
    w: JsonWriter,
}

impl Default for JsonWriterSink {
    fn default() -> Self {
        Self::new()
    }
}

impl JsonWriterSink {
    pub fn new() -> Self {
        Self {
            w: JsonWriter::new(),
        }
    }
}

impl<'py> DumpSink<'py> for JsonWriterSink {
    type Out = Vec<u8>;

    fn leaf(&mut self, key: Option<&str>, v: &Bound<'py, PyAny>) -> Result<(), SerializationError> {
        write_leaf(&mut self.w, key, v)
    }

    fn null(&mut self, key: Option<&str>) -> Result<(), SerializationError> {
        self.w.value_null(key);
        Ok(())
    }

    fn pyobject(
        &mut self,
        key: Option<&str>,
        v: &Bound<'py, PyAny>,
    ) -> Result<(), SerializationError> {
        write_pyobject(&mut self.w, key, v)
    }

    fn open_object<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>,
    {
        let frame = self.w.begin_object(key);
        match body(self) {
            Ok(()) => {
                self.w.end_object();
                Ok(())
            }
            Err(e) => {
                self.w.rollback(frame);
                Err(e)
            }
        }
    }

    fn open_array<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>,
    {
        let frame = self.w.begin_array(key);
        match body(self) {
            Ok(()) => {
                self.w.end_array();
                Ok(())
            }
            Err(e) => {
                self.w.rollback(frame);
                Err(e)
            }
        }
    }

    fn finish(self) -> Self::Out {
        self.w.into_bytes()
    }
}

pub fn wrap_value_error(py: Python<'_>, e: &SerializationError) -> SerializationError {
    let nested = PyDict::new(py);
    let _ = nested.set_item("value", e.to_py_value(py).unwrap_or_else(|_| py.None()));
    SerializationError::Dict(nested.unbind())
}

fn write_leaf(
    w: &mut JsonWriter,
    key: Option<&str>,
    v: &Bound<'_, PyAny>,
) -> Result<(), SerializationError> {
    let py = v.py();
    if v.is_none() {
        w.value_null(key);
    } else if v.is_instance_of::<PyBool>() {
        w.value_bool(key, v.extract::<bool>().unwrap_or(false));
    } else if let Ok(s) = v.cast::<PyString>() {
        let s = s
            .to_str()
            .map_err(|e| SerializationError::from_pyerr(py, &e))?;
        w.value_str(key, s);
    } else if v.is_instance_of::<PyInt>() {
        write_pyint(w, key, v)?;
    } else if v.is_instance_of::<PyFloat>() {
        let f = v
            .extract::<f64>()
            .map_err(|e| SerializationError::from_pyerr(py, &e))?;
        w.value_f64(key, f);
    } else {
        return Err(SerializationError::simple(py, ANY_ERROR));
    }
    Ok(())
}

fn write_pyint(
    w: &mut JsonWriter,
    key: Option<&str>,
    v: &Bound<'_, PyAny>,
) -> Result<(), SerializationError> {
    let py = v.py();
    if let Ok(i) = v.extract::<i64>() {
        w.value_i64(key, i);
    } else {
        let s = v
            .str()
            .map_err(|e| SerializationError::from_pyerr(py, &e))?;
        let s = s
            .to_str()
            .map_err(|e| SerializationError::from_pyerr(py, &e))?;
        w.value_number_str(key, s);
    }
    Ok(())
}

fn write_pyobject(
    w: &mut JsonWriter,
    key: Option<&str>,
    v: &Bound<'_, PyAny>,
) -> Result<(), SerializationError> {
    let py = v.py();
    if v.is_none() {
        w.value_null(key);
    } else if v.is_instance_of::<PyBool>() {
        w.value_bool(key, v.extract::<bool>().unwrap_or(false));
    } else if v.is_instance_of::<PyInt>() {
        write_pyint(w, key, v)?;
    } else if let Ok(s) = v.cast::<PyString>() {
        let s = s
            .to_str()
            .map_err(|e| SerializationError::from_pyerr(py, &e))?;
        w.value_str(key, s);
    } else if v.is_instance_of::<PyFloat>() {
        let f = v
            .extract::<f64>()
            .map_err(|e| SerializationError::from_pyerr(py, &e))?;
        if !f.is_finite() {
            return Err(SerializationError::Single(
                intern!(py, ANY_ERROR).clone().unbind(),
            ));
        }
        w.value_f64(key, f);
    } else if let Ok(list) = v.cast::<PyList>() {
        w.array(key, |w| {
            for item in list.iter() {
                write_pyobject(w, None, &item)?;
            }
            Ok(())
        })?;
    } else if let Ok(dict) = v.cast::<PyDict>() {
        w.object(key, |w| {
            for (k, val) in dict.iter() {
                let ks = k.cast::<PyString>().map_err(|_| {
                    SerializationError::Single(intern!(py, ANY_ERROR).clone().unbind())
                })?;
                let ks = ks
                    .to_str()
                    .map_err(|e| SerializationError::from_pyerr(py, &e))?;
                write_pyobject(w, Some(ks), &val)?;
            }
            Ok(())
        })?;
    } else {
        return Err(SerializationError::Single(
            intern!(py, ANY_ERROR).clone().unbind(),
        ));
    }
    Ok(())
}
