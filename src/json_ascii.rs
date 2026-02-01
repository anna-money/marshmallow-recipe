use serde::Serialize;
use std::io::{self, Write};

struct AsciiFormatter;

impl serde_json::ser::Formatter for AsciiFormatter {
    fn write_string_fragment<W>(&mut self, writer: &mut W, fragment: &str) -> io::Result<()>
    where
        W: ?Sized + Write,
    {
        for ch in fragment.chars() {
            if ch.is_ascii() {
                write!(writer, "{ch}")?;
            } else {
                for code_unit in ch.encode_utf16(&mut [0; 2]) {
                    write!(writer, "\\u{code_unit:04x}")?;
                }
            }
        }
        Ok(())
    }
}

pub fn to_vec<T: Serialize>(value: &T) -> serde_json::Result<Vec<u8>> {
    let mut writer = Vec::with_capacity(128);
    let mut serializer = serde_json::Serializer::with_formatter(&mut writer, AsciiFormatter);
    value.serialize(&mut serializer)?;
    Ok(writer)
}
