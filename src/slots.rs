use pyo3::prelude::*;

#[inline]
pub unsafe fn get_slot_value_direct<'py>(
    py: Python<'py>,
    obj: &Bound<'_, PyAny>,
    offset: isize,
) -> Option<Bound<'py, PyAny>> {
    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return None;
    }
    let slot_ptr = (obj_ptr as *const u8).offset(offset) as *const *mut pyo3::ffi::PyObject;
    let py_obj_ptr = *slot_ptr;
    if py_obj_ptr.is_null() {
        return None;
    }
    Some(Py::<PyAny>::from_borrowed_ptr(py, py_obj_ptr).into_bound(py))
}

#[inline]
pub unsafe fn set_slot_value_direct(
    obj: &Bound<'_, PyAny>,
    offset: isize,
    value: Py<PyAny>,
) {
    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return;
    }
    let slot_ptr = (obj_ptr as *mut u8).offset(offset) as *mut *mut pyo3::ffi::PyObject;
    let old_ptr = *slot_ptr;
    let new_ptr = value.into_ptr();
    *slot_ptr = new_ptr;
    if !old_ptr.is_null() {
        pyo3::ffi::Py_DECREF(old_ptr);
    }
}
