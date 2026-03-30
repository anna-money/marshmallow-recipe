use pyo3::prelude::*;

#[allow(clippy::cast_ptr_alignment)]
pub unsafe fn get_slot_value_direct<'py>(
    py: Python<'py>,
    obj: &Bound<'_, PyAny>,
    offset: isize,
) -> Option<Bound<'py, PyAny>> {
    debug_assert!(
        offset
            .cast_unsigned()
            .is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()),
        "slot offset {offset} is not properly aligned"
    );

    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return None;
    }

    let basicsize = unsafe { (*(*obj_ptr).ob_type).tp_basicsize };
    if basicsize <= 0 {
        return None;
    }
    let end = offset.cast_unsigned() + std::mem::size_of::<*mut pyo3::ffi::PyObject>();
    if end > basicsize.cast_unsigned() {
        return None;
    }

    unsafe {
        let slot_ptr = (obj_ptr as *const u8)
            .offset(offset)
            .cast::<*mut pyo3::ffi::PyObject>();
        let py_obj_ptr = *slot_ptr;
        Bound::from_borrowed_ptr_or_opt(py, py_obj_ptr)
    }
}

#[allow(clippy::cast_ptr_alignment)]
pub unsafe fn set_slot_value_direct(
    obj: &Bound<'_, PyAny>,
    offset: isize,
    value: Py<PyAny>,
) -> bool {
    debug_assert!(
        offset
            .cast_unsigned()
            .is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()),
        "slot offset {offset} is not properly aligned"
    );

    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return false;
    }

    let basicsize = unsafe { (*(*obj_ptr).ob_type).tp_basicsize };
    if basicsize <= 0 {
        return false;
    }
    let end = offset.cast_unsigned() + std::mem::size_of::<*mut pyo3::ffi::PyObject>();
    if end > basicsize.cast_unsigned() {
        return false;
    }

    unsafe {
        let slot_ptr = obj_ptr
            .cast::<u8>()
            .offset(offset)
            .cast::<*mut pyo3::ffi::PyObject>();
        let old_ptr = *slot_ptr;
        let new_ptr = value.into_ptr();
        *slot_ptr = new_ptr;
        if !old_ptr.is_null() {
            pyo3::ffi::Py_DECREF(old_ptr);
        }
    }
    true
}
