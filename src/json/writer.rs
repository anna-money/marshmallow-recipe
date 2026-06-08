use pyo3::prelude::*;
use pyo3::types::PyString;

const HEX: &[u8; 16] = b"0123456789abcdef";

pub struct JsonWriter {
    buf: Vec<u8>,
}

impl Default for JsonWriter {
    fn default() -> Self {
        Self::new()
    }
}

impl JsonWriter {
    pub fn new() -> Self {
        Self {
            buf: Vec::with_capacity(256),
        }
    }

    pub fn into_bytes(self) -> Vec<u8> {
        self.buf
    }

    pub const fn len(&self) -> usize {
        self.buf.len()
    }

    pub fn truncate(&mut self, n: usize) {
        self.buf.truncate(n);
    }

    pub fn push(&mut self, b: u8) {
        self.buf.push(b);
    }

    pub fn write_null(&mut self) {
        self.buf.extend_from_slice(b"null");
    }

    pub fn write_bool(&mut self, b: bool) {
        self.buf
            .extend_from_slice(if b { b"true" } else { b"false" });
    }

    pub fn write_i64(&mut self, i: i64) {
        const DIGITS: &[u8; 10] = b"0123456789";
        let mut tmp = [0u8; 20];
        let mut idx = tmp.len();
        let mut m = i.unsigned_abs();
        loop {
            idx -= 1;
            tmp[idx] = DIGITS[usize::try_from(m % 10).unwrap_or(0)];
            m /= 10;
            if m == 0 {
                break;
            }
        }
        if i < 0 {
            self.buf.push(b'-');
        }
        self.buf.extend_from_slice(&tmp[idx..]);
    }

    pub fn write_pyint(&mut self, v: &Bound<'_, PyAny>) -> PyResult<()> {
        if let Ok(i) = v.extract::<i64>() {
            self.write_i64(i);
        } else {
            let s = v.str()?;
            self.buf.extend_from_slice(s.to_str()?.as_bytes());
        }
        Ok(())
    }

    pub fn write_f64(&mut self, f: f64) {
        if f.is_nan() {
            self.buf.extend_from_slice(b"NaN");
            return;
        }
        if f.is_infinite() {
            self.buf
                .extend_from_slice(if f < 0.0 { b"-Infinity" } else { b"Infinity" });
            return;
        }
        unsafe {
            let ptr = pyo3::ffi::PyOS_double_to_string(
                f,
                b'r'.cast_signed(),
                0,
                pyo3::ffi::Py_DTSF_ADD_DOT_0,
                std::ptr::null_mut(),
            );
            if ptr.is_null() {
                return;
            }
            let cstr = std::ffi::CStr::from_ptr(ptr);
            self.buf.extend_from_slice(cstr.to_bytes());
            pyo3::ffi::PyMem_Free(ptr.cast());
        }
    }

    fn write_unicode_escape(&mut self, cp: u32) {
        self.buf.extend_from_slice(b"\\u");
        self.buf.push(HEX[((cp >> 12) & 0xf) as usize]);
        self.buf.push(HEX[((cp >> 8) & 0xf) as usize]);
        self.buf.push(HEX[((cp >> 4) & 0xf) as usize]);
        self.buf.push(HEX[(cp & 0xf) as usize]);
    }

    pub fn write_str(&mut self, s: &str) {
        self.buf.push(b'"');
        for c in s.chars() {
            match c {
                '"' => self.buf.extend_from_slice(b"\\\""),
                '\\' => self.buf.extend_from_slice(b"\\\\"),
                '\n' => self.buf.extend_from_slice(b"\\n"),
                '\r' => self.buf.extend_from_slice(b"\\r"),
                '\t' => self.buf.extend_from_slice(b"\\t"),
                '\u{08}' => self.buf.extend_from_slice(b"\\b"),
                '\u{0c}' => self.buf.extend_from_slice(b"\\f"),
                c if (c as u32) < 0x20 => self.write_unicode_escape(c as u32),
                c if (c as u32) < 0x7f => self.buf.push(c as u8),
                c => {
                    let cp = c as u32;
                    if cp <= 0xffff {
                        self.write_unicode_escape(cp);
                    } else {
                        let v = cp - 0x10000;
                        self.write_unicode_escape(0xd800 + (v >> 10));
                        self.write_unicode_escape(0xdc00 + (v & 0x3ff));
                    }
                }
            }
        }
        self.buf.push(b'"');
    }

    pub fn write_str_value(&mut self, v: &Bound<'_, PyString>) -> PyResult<()> {
        self.write_str(v.to_str()?);
        Ok(())
    }
}
