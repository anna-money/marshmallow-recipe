use pyo3::prelude::*;

// These functions provide direct memory access to Python object slots,
// bypassing the normal attribute access mechanism for better performance.
//
// SAFETY: The offset must be properly aligned for pointer access.
// This is guaranteed by filtering out unaligned offsets when extracting
// slot_offset in cache.rs and types.rs. We use debug_assert! to catch
// any misuse during development.
//
// The cast_ptr_alignment warning is suppressed because:
// 1. Python objects are allocated via malloc, which returns aligned pointers
// 2. We verify that offset is aligned before it reaches these functions
// 3. Therefore (obj_ptr + offset) is guaranteed to be properly aligned

#[inline]
#[allow(clippy::cast_ptr_alignment)]
pub unsafe fn get_slot_value_direct<'py>(
    py: Python<'py>,
    obj: &Bound<'_, PyAny>,
    offset: isize,
) -> Option<Bound<'py, PyAny>> {
    debug_assert!(
        offset.cast_unsigned().is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()),
        "slot offset {offset} is not properly aligned"
    );

    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return None;
    }
    let slot_ptr = (obj_ptr as *const u8).offset(offset).cast::<*mut pyo3::ffi::PyObject>();
    let py_obj_ptr = *slot_ptr;
    Bound::from_borrowed_ptr_or_opt(py, py_obj_ptr)
}

#[inline]
#[allow(clippy::cast_ptr_alignment)]
pub unsafe fn set_slot_value_direct(
    obj: &Bound<'_, PyAny>,
    offset: isize,
    value: Py<PyAny>,
) {
    debug_assert!(
        offset.cast_unsigned().is_multiple_of(std::mem::align_of::<*mut pyo3::ffi::PyObject>()),
        "slot offset {offset} is not properly aligned"
    );

    let obj_ptr = obj.as_ptr();
    if obj_ptr.is_null() {
        return;
    }
    let slot_ptr = obj_ptr.cast::<u8>().offset(offset).cast::<*mut pyo3::ffi::PyObject>();
    let old_ptr = *slot_ptr;
    let new_ptr = value.into_ptr();
    *slot_ptr = new_ptr;
    if !old_ptr.is_null() {
        pyo3::ffi::Py_DECREF(old_ptr);
    }
}
