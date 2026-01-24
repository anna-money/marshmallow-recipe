mod types;
mod encoding;
mod slots;
mod cache;
mod utils;
mod fields;
mod load_bytes;
mod dump_bytes;
mod dump;
mod load;
mod api;
mod dumper;
mod loader;

use pyo3::prelude::*;

#[cfg(feature = "alloc-stats")]
use std::sync::atomic::Ordering;

#[cfg(feature = "alloc-stats")]
mod alloc_stats {
    use std::alloc::{GlobalAlloc, Layout, System};
    use std::sync::atomic::{AtomicUsize, Ordering};

    pub static ALLOCATED: AtomicUsize = AtomicUsize::new(0);
    pub static DEALLOCATED: AtomicUsize = AtomicUsize::new(0);
    pub static ALLOC_COUNT: AtomicUsize = AtomicUsize::new(0);
    pub static DEALLOC_COUNT: AtomicUsize = AtomicUsize::new(0);

    pub struct CountingAlloc;

    unsafe impl GlobalAlloc for CountingAlloc {
        unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
            ALLOCATED.fetch_add(layout.size(), Ordering::Relaxed);
            ALLOC_COUNT.fetch_add(1, Ordering::Relaxed);
            System.alloc(layout)
        }

        unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
            DEALLOCATED.fetch_add(layout.size(), Ordering::Relaxed);
            DEALLOC_COUNT.fetch_add(1, Ordering::Relaxed);
            System.dealloc(ptr, layout);
        }
    }

    #[global_allocator]
    static GLOBAL: CountingAlloc = CountingAlloc;
}

#[cfg(feature = "alloc-stats")]
#[pyfunction]
fn reset_alloc_stats() {
    alloc_stats::ALLOCATED.store(0, Ordering::Relaxed);
    alloc_stats::DEALLOCATED.store(0, Ordering::Relaxed);
    alloc_stats::ALLOC_COUNT.store(0, Ordering::Relaxed);
    alloc_stats::DEALLOC_COUNT.store(0, Ordering::Relaxed);
}

#[cfg(feature = "alloc-stats")]
#[pyfunction]
fn get_alloc_stats() -> (usize, usize, usize, usize) {
    (
        alloc_stats::ALLOCATED.load(Ordering::Relaxed),
        alloc_stats::DEALLOCATED.load(Ordering::Relaxed),
        alloc_stats::ALLOC_COUNT.load(Ordering::Relaxed),
        alloc_stats::DEALLOC_COUNT.load(Ordering::Relaxed),
    )
}

#[pymodule]
fn _nuked(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cache::register, m)?)?;
    m.add_function(wrap_pyfunction!(api::load, m)?)?;
    m.add_function(wrap_pyfunction!(api::dump, m)?)?;
    m.add_function(wrap_pyfunction!(api::load_from_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(api::dump_to_bytes, m)?)?;
    #[cfg(feature = "alloc-stats")]
    {
        m.add_function(wrap_pyfunction!(reset_alloc_stats, m)?)?;
        m.add_function(wrap_pyfunction!(get_alloc_stats, m)?)?;
    }
    Ok(())
}
