mod types;
mod encoding;
mod slots;
mod cache;
mod utils;
mod deserialize_bytes;
mod serialize_bytes;
mod serialize;
mod deserialize;
mod api;

use pyo3::prelude::*;

#[pymodule]
fn _nuked(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cache::register, m)?)?;
    m.add_function(wrap_pyfunction!(api::load, m)?)?;
    m.add_function(wrap_pyfunction!(api::dump, m)?)?;
    m.add_function(wrap_pyfunction!(api::load_from_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(api::dump_to_bytes, m)?)?;
    Ok(())
}
