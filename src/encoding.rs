use encoding_rs::Encoding;
use pyo3::prelude::*;
use std::borrow::Cow;

fn normalize_encoding_label(encoding: &str) -> &str {
    if encoding.eq_ignore_ascii_case("latin-1")
        || encoding.eq_ignore_ascii_case("latin1")
        || encoding.eq_ignore_ascii_case("iso-8859-1")
        || encoding.eq_ignore_ascii_case("iso8859-1")
    {
        return "windows-1252";
    }
    encoding
}

pub fn decode_to_utf8_bytes<'a>(bytes: &'a [u8], encoding: &str) -> PyResult<Cow<'a, [u8]>> {
    if encoding.eq_ignore_ascii_case("utf-8") || encoding.eq_ignore_ascii_case("utf8") {
        return Ok(Cow::Borrowed(bytes));
    }
    if encoding.eq_ignore_ascii_case("ascii") {
        if bytes.iter().any(|&b| b > 127) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "ASCII decoding error: byte > 127"
            ));
        }
        return Ok(Cow::Borrowed(bytes));
    }
    let label = normalize_encoding_label(encoding);
    let enc = Encoding::for_label(label.as_bytes())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown encoding: {}", encoding)
        ))?;
    let mut decoder = enc.new_decoder();
    let max_len = decoder.max_utf8_buffer_length(bytes.len())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Buffer size overflow"))?;
    let mut output = vec![0u8; max_len];
    let (result, _, written, _) = decoder.decode_to_utf8(bytes, &mut output, true);
    if result == encoding_rs::CoderResult::InputEmpty {
        output.truncate(written);
        Ok(Cow::Owned(output))
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to decode with encoding: {}", enc.name())
        ))
    }
}

pub fn encode_from_utf8_bytes<'a>(utf8_bytes: &'a [u8], encoding: &str) -> PyResult<Cow<'a, [u8]>> {
    if encoding.eq_ignore_ascii_case("utf-8") || encoding.eq_ignore_ascii_case("utf8") {
        return Ok(Cow::Borrowed(utf8_bytes));
    }
    if encoding.eq_ignore_ascii_case("ascii") {
        if utf8_bytes.iter().any(|&b| b > 127) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "ASCII encoding error: non-ASCII character in output"
            ));
        }
        return Ok(Cow::Borrowed(utf8_bytes));
    }
    let label = normalize_encoding_label(encoding);
    let enc = Encoding::for_label(label.as_bytes())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown encoding: {}", encoding)
        ))?;
    let utf8_str = std::str::from_utf8(utf8_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    let mut encoder = enc.new_encoder();
    let max_len = encoder.max_buffer_length_from_utf8_if_no_unmappables(utf8_str.len())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Buffer size overflow"))?;
    let mut output = vec![0u8; max_len];
    let (result, _, written, _) = encoder.encode_from_utf8(utf8_str, &mut output, true);
    if result == encoding_rs::CoderResult::InputEmpty {
        output.truncate(written);
        Ok(Cow::Owned(output))
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to encode with encoding: {}", enc.name())
        ))
    }
}
