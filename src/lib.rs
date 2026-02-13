mod builder;
mod container;
mod container_dump;
mod container_load;
mod error;
mod fields;
mod slots;
mod utils;

use pyo3::prelude::*;

#[pymodule]
fn _nuked(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<builder::ContainerBuilder>()?;
    m.add_class::<builder::FieldHandle>()?;
    m.add_class::<builder::DataclassHandle>()?;
    m.add_class::<builder::TypeHandle>()?;
    m.add_class::<builder::Container>()?;
    Ok(())
}
