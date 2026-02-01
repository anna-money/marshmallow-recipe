use encoding_rs::{CoderResult, EncoderResult, Encoding};
use pyo3::exceptions::{PyUnicodeDecodeError, PyUnicodeEncodeError, PyValueError};
use pyo3::prelude::*;
use std::borrow::Cow;

#[inline]
const fn is_utf8(encoding: &str) -> bool {
    encoding.eq_ignore_ascii_case("utf-8") || encoding.eq_ignore_ascii_case("utf8")
}

#[inline]
const fn is_ascii(encoding: &str) -> bool {
    encoding.eq_ignore_ascii_case("ascii")
}

fn get_encoding(encoding: &str) -> PyResult<&'static Encoding> {
    const LATIN1_ALIASES: [&str; 4] = ["latin-1", "latin1", "iso-8859-1", "iso8859-1"];
    let label = if LATIN1_ALIASES
        .iter()
        .any(|alias| encoding.eq_ignore_ascii_case(alias))
    {
        "windows-1252"
    } else {
        encoding
    };
    Encoding::for_label(label.as_bytes())
        .ok_or_else(|| PyValueError::new_err(format!("Unknown encoding: {encoding}")))
}

fn buffer_overflow_error() -> PyErr {
    PyValueError::new_err("Buffer size overflow")
}

fn make_decode_error(py: Python<'_>, encoding: &str, bytes: &[u8], pos: usize) -> PyErr {
    PyUnicodeDecodeError::new(
        py,
        std::ffi::CString::new(encoding).unwrap().as_c_str(),
        bytes,
        pos..pos + 1,
        c"ordinal not in range(128)",
    )
    .map_or_else(|e| e, |e| PyErr::from_value(e.into_any()))
}

fn make_encode_error(
    py: Python<'_>,
    encoding: &str,
    text: &str,
    start: usize,
    end: usize,
    reason: &str,
) -> PyErr {
    let exc_type = py.get_type::<PyUnicodeEncodeError>();
    let args = (
        encoding.to_owned(),
        text.to_owned(),
        start,
        end,
        reason.to_owned(),
    );
    PyErr::from_type(exc_type, args)
}

pub fn decode_to_utf8_bytes<'a>(
    py: Python<'_>,
    bytes: &'a [u8],
    encoding: &str,
) -> PyResult<Cow<'a, [u8]>> {
    if is_utf8(encoding) {
        return Ok(Cow::Borrowed(bytes));
    }
    if is_ascii(encoding) {
        if let Some(pos) = bytes.iter().position(|&b| b > 127) {
            return Err(make_decode_error(py, encoding, bytes, pos));
        }
        return Ok(Cow::Borrowed(bytes));
    }
    let enc = get_encoding(encoding)?;
    let mut decoder = enc.new_decoder();
    let max_len = decoder
        .max_utf8_buffer_length(bytes.len())
        .ok_or_else(buffer_overflow_error)?;
    let mut output = vec![0u8; max_len];
    let (result, _, written, _) = decoder.decode_to_utf8(bytes, &mut output, true);
    if result == CoderResult::InputEmpty {
        output.truncate(written);
        Ok(Cow::Owned(output))
    } else {
        Err(make_decode_error(py, enc.name(), bytes, 0))
    }
}

pub fn encode_from_utf8_bytes<'a>(
    py: Python<'_>,
    utf8_bytes: &'a [u8],
    encoding: &str,
) -> PyResult<Cow<'a, [u8]>> {
    if is_utf8(encoding) {
        return Ok(Cow::Borrowed(utf8_bytes));
    }
    let utf8_str =
        std::str::from_utf8(utf8_bytes).map_err(|e| PyValueError::new_err(e.to_string()))?;
    if is_ascii(encoding) {
        if let Some((pos, ch)) = utf8_str.char_indices().find(|(_, c)| !c.is_ascii()) {
            return Err(make_encode_error(
                py,
                encoding,
                utf8_str,
                pos,
                pos + ch.len_utf8(),
                "ordinal not in range(128)",
            ));
        }
        return Ok(Cow::Borrowed(utf8_bytes));
    }
    let enc = get_encoding(encoding)?;
    let mut encoder = enc.new_encoder();
    let mut output = Vec::with_capacity(128);
    let (result, _) =
        encoder.encode_from_utf8_to_vec_without_replacement(utf8_str, &mut output, true);
    if result == EncoderResult::InputEmpty {
        Ok(Cow::Owned(output))
    } else {
        Err(make_encode_error(
            py,
            enc.name(),
            utf8_str,
            0,
            utf8_str.len(),
            "character maps to <undefined>",
        ))
    }
}
