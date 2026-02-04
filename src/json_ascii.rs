use serde::Serialize;
use std::io::{self, Write};

struct AsciiFormatter;

impl serde_json::ser::Formatter for AsciiFormatter {
    fn write_string_fragment<W>(&mut self, writer: &mut W, fragment: &str) -> io::Result<()>
    where
        W: ?Sized + Write,
    {
        let mut start = 0;

        for (i, ch) in fragment.char_indices() {
            if !ch.is_ascii() {
                if start < i {
                    writer.write_all(&fragment.as_bytes()[start..i])?;
                }
                for code_unit in ch.encode_utf16(&mut [0; 2]) {
                    write!(writer, "\\u{code_unit:04x}")?;
                }
                start = i + ch.len_utf8();
            }
        }

        if start < fragment.len() {
            writer.write_all(&fragment.as_bytes()[start..])?;
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
