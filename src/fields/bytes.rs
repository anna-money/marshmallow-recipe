use base64::Engine;
use base64::encoded_len;
use base64::engine::general_purpose::STANDARD;
use pyo3::ffi;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyString};

use crate::error::SerializationError;

pub fn load_from_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    if value.is_instance_of::<PyBytes>() {
        return Ok(value.clone().unbind());
    }
    if let Ok(py_str) = value.cast::<PyString>()
        && let Ok(s) = py_str.to_str()
    {
        let input = s.as_bytes();
        let padding = input.iter().rev().take(2).filter(|&&b| b == b'=').count();
        let decoded_len = (input.len() / 4 * 3).saturating_sub(padding);
        return PyBytes::new_with(py, decoded_len, |buf| {
            STANDARD
                .decode_slice(s, buf)
                .map(|_| ())
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
        })
        .map(|b| b.into_any().unbind())
        .map_err(|_| SerializationError::Single(invalid_error.clone_ref(py)));
    }
    Err(SerializationError::Single(invalid_error.clone_ref(py)))
}

pub fn dump_to_py(
    value: &Bound<'_, PyAny>,
    invalid_error: &Py<PyString>,
) -> Result<Py<PyAny>, SerializationError> {
    let py = value.py();
    if !value.is_instance_of::<PyBytes>() {
        return Err(SerializationError::Single(invalid_error.clone_ref(py)));
    }
    let bytes: &[u8] = value.extract().expect("already checked type");
    let encoded_len =
        encoded_len(bytes.len(), true).expect("usize overflow when calculating encoded length");
    unsafe {
        let ptr = ffi::PyUnicode_New(encoded_len.cast_signed(), 127);
        let obj = Bound::from_owned_ptr_or_err(py, ptr).expect("failed to allocate unicode object");
        let buf =
            std::slice::from_raw_parts_mut(ffi::PyUnicode_1BYTE_DATA(obj.as_ptr()), encoded_len);
        STANDARD
            .encode_slice(bytes, buf)
            .expect("buffer is correctly sized");
        Ok(obj.into_any().unbind())
    }
}
