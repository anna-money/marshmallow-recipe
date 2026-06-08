use std::io::Write;

use crate::error::SerializationError;

const HEX: &[u8; 16] = b"0123456789abcdef";

#[derive(Clone, Copy)]
pub struct Frame {
    mark: usize,
    had_first: bool,
}

pub struct JsonWriter {
    buf: Vec<u8>,
    first: bool,
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
            first: true,
        }
    }

    pub fn into_bytes(self) -> Vec<u8> {
        self.buf
    }

    fn pre(&mut self, key: Option<&str>) {
        if !self.first {
            self.buf.push(b',');
        }
        self.first = false;
        if let Some(k) = key {
            self.fmt_str(k);
            self.buf.push(b':');
        }
    }

    pub fn value_null(&mut self, key: Option<&str>) {
        self.pre(key);
        self.buf.extend_from_slice(b"null");
    }

    pub fn value_bool(&mut self, key: Option<&str>, b: bool) {
        self.pre(key);
        self.buf
            .extend_from_slice(if b { b"true" } else { b"false" });
    }

    pub fn value_i64(&mut self, key: Option<&str>, i: i64) {
        self.pre(key);
        self.fmt_i64(i);
    }

    pub fn value_number_str(&mut self, key: Option<&str>, digits: &str) {
        self.pre(key);
        self.buf.extend_from_slice(digits.as_bytes());
    }

    pub fn value_f64(&mut self, key: Option<&str>, f: f64) {
        self.pre(key);
        self.fmt_f64(f);
    }

    pub fn value_str(&mut self, key: Option<&str>, s: &str) {
        self.pre(key);
        self.fmt_str(s);
    }

    pub fn begin_object(&mut self, key: Option<&str>) -> Frame {
        let mark = self.buf.len();
        let had_first = self.first;
        self.pre(key);
        self.buf.push(b'{');
        self.first = true;
        Frame { mark, had_first }
    }

    pub fn end_object(&mut self) {
        self.buf.push(b'}');
        self.first = false;
    }

    pub fn begin_array(&mut self, key: Option<&str>) -> Frame {
        let mark = self.buf.len();
        let had_first = self.first;
        self.pre(key);
        self.buf.push(b'[');
        self.first = true;
        Frame { mark, had_first }
    }

    pub fn end_array(&mut self) {
        self.buf.push(b']');
        self.first = false;
    }

    pub fn rollback(&mut self, frame: Frame) {
        self.buf.truncate(frame.mark);
        self.first = frame.had_first;
    }

    pub fn object<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>,
    {
        let frame = self.begin_object(key);
        match body(self) {
            Ok(()) => {
                self.end_object();
                Ok(())
            }
            Err(e) => {
                self.rollback(frame);
                Err(e)
            }
        }
    }

    pub fn array<F>(&mut self, key: Option<&str>, body: F) -> Result<(), SerializationError>
    where
        F: FnOnce(&mut Self) -> Result<(), SerializationError>,
    {
        let frame = self.begin_array(key);
        match body(self) {
            Ok(()) => {
                self.end_array();
                Ok(())
            }
            Err(e) => {
                self.rollback(frame);
                Err(e)
            }
        }
    }

    fn fmt_i64(&mut self, i: i64) {
        write!(self.buf, "{i}").expect("writing to Vec<u8> must not fail");
    }

    fn fmt_f64(&mut self, f: f64) {
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

    fn fmt_str(&mut self, s: &str) {
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
}
