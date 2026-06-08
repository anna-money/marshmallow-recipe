use pyo3::conversion::IntoPyObjectExt;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyList, PyString};

use crate::error::SerializationError;

const MAX_DEPTH: usize = 256;

fn push_char(out: &mut Vec<u8>, c: char) {
    let mut b = [0u8; 4];
    out.extend_from_slice(c.encode_utf8(&mut b).as_bytes());
}

pub struct Parser<'a> {
    d: &'a [u8],
    i: usize,
    depth: usize,
}

impl<'a> Parser<'a> {
    pub const fn new(d: &'a [u8]) -> Self {
        Self { d, i: 0, depth: 0 }
    }

    fn err(py: Python<'_>, msg: &str) -> SerializationError {
        SerializationError::simple(py, &format!("Invalid JSON: {msg}"))
    }

    pub fn skip_ws(&mut self) {
        while self.i < self.d.len() && matches!(self.d[self.i], b' ' | b'\t' | b'\n' | b'\r') {
            self.i += 1;
        }
    }

    fn peek(&self, py: Python<'_>) -> Result<u8, SerializationError> {
        self.d
            .get(self.i)
            .copied()
            .ok_or_else(|| Self::err(py, "unexpected end of input"))
    }

    pub fn peek_byte(&mut self) -> Option<u8> {
        self.skip_ws();
        self.d.get(self.i).copied()
    }

    pub fn at_end(&mut self) -> bool {
        self.skip_ws();
        self.i >= self.d.len()
    }

    pub const fn bump(&mut self) {
        self.i += 1;
    }

    pub fn expect(&mut self, py: Python<'_>, b: u8) -> Result<(), SerializationError> {
        self.skip_ws();
        if self.peek(py)? == b {
            self.i += 1;
            Ok(())
        } else {
            Err(Self::err(py, "unexpected character"))
        }
    }

    fn lit(&mut self, py: Python<'_>, s: &str) -> Result<(), SerializationError> {
        for &b in s.as_bytes() {
            if self.peek(py)? != b {
                return Err(Self::err(py, "invalid literal"));
            }
            self.i += 1;
        }
        Ok(())
    }

    fn hex4(&mut self, py: Python<'_>) -> Result<u32, SerializationError> {
        let mut v = 0u32;
        for _ in 0..4 {
            let c = self.peek(py)?;
            self.i += 1;
            let d = match c {
                b'0'..=b'9' => u32::from(c - b'0'),
                b'a'..=b'f' => u32::from(c - b'a' + 10),
                b'A'..=b'F' => u32::from(c - b'A' + 10),
                _ => return Err(Self::err(py, "invalid \\u escape")),
            };
            v = v * 16 + d;
        }
        Ok(v)
    }

    pub fn parse_string_raw(&mut self, py: Python<'_>) -> Result<String, SerializationError> {
        self.skip_ws();
        if self.peek(py)? != b'"' {
            return Err(Self::err(py, "expected string"));
        }
        self.i += 1;
        let mut out: Vec<u8> = Vec::new();
        loop {
            let c = self.peek(py)?;
            self.i += 1;
            match c {
                b'"' => break,
                b'\\' => {
                    let e = self.peek(py)?;
                    self.i += 1;
                    match e {
                        b'"' => out.push(b'"'),
                        b'\\' => out.push(b'\\'),
                        b'/' => out.push(b'/'),
                        b'b' => out.push(0x08),
                        b'f' => out.push(0x0c),
                        b'n' => out.push(b'\n'),
                        b'r' => out.push(b'\r'),
                        b't' => out.push(b'\t'),
                        b'u' => {
                            let cp = self.hex4(py)?;
                            if (0xD800..=0xDBFF).contains(&cp) {
                                if self.peek(py)? != b'\\' {
                                    return Err(Self::err(py, "expected low surrogate"));
                                }
                                self.i += 1;
                                if self.peek(py)? != b'u' {
                                    return Err(Self::err(py, "expected low surrogate"));
                                }
                                self.i += 1;
                                let lo = self.hex4(py)?;
                                if !(0xDC00..=0xDFFF).contains(&lo) {
                                    return Err(Self::err(py, "invalid low surrogate"));
                                }
                                let combined = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                                push_char(
                                    &mut out,
                                    char::from_u32(combined)
                                        .ok_or_else(|| Self::err(py, "invalid code point"))?,
                                );
                            } else if (0xDC00..=0xDFFF).contains(&cp) {
                                return Err(Self::err(py, "unexpected low surrogate"));
                            } else {
                                push_char(
                                    &mut out,
                                    char::from_u32(cp)
                                        .ok_or_else(|| Self::err(py, "invalid code point"))?,
                                );
                            }
                        }
                        _ => return Err(Self::err(py, "invalid escape")),
                    }
                }
                0x00..=0x1f => return Err(Self::err(py, "control character in string")),
                _ => out.push(c),
            }
        }
        String::from_utf8(out).map_err(|_| Self::err(py, "invalid utf-8"))
    }

    fn parse_number_slice(
        &mut self,
        py: Python<'_>,
    ) -> Result<(&'a str, bool), SerializationError> {
        let start = self.i;
        let mut is_float = false;
        if self.peek(py)? == b'-' {
            self.i += 1;
        }
        match self.peek(py)? {
            b'0' => {
                self.i += 1;
                if self.i < self.d.len() && self.d[self.i].is_ascii_digit() {
                    return Err(Self::err(py, "leading zero"));
                }
            }
            b'1'..=b'9' => {
                while self.i < self.d.len() && self.d[self.i].is_ascii_digit() {
                    self.i += 1;
                }
            }
            _ => return Err(Self::err(py, "invalid number")),
        }
        if self.i < self.d.len() && self.d[self.i] == b'.' {
            is_float = true;
            self.i += 1;
            if !(self.i < self.d.len() && self.d[self.i].is_ascii_digit()) {
                return Err(Self::err(py, "invalid number"));
            }
            while self.i < self.d.len() && self.d[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }
        if self.i < self.d.len() && (self.d[self.i] == b'e' || self.d[self.i] == b'E') {
            is_float = true;
            self.i += 1;
            if self.i < self.d.len() && (self.d[self.i] == b'+' || self.d[self.i] == b'-') {
                self.i += 1;
            }
            if !(self.i < self.d.len() && self.d[self.i].is_ascii_digit()) {
                return Err(Self::err(py, "invalid number"));
            }
            while self.i < self.d.len() && self.d[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }
        let s = std::str::from_utf8(&self.d[start..self.i])
            .map_err(|_| Self::err(py, "invalid number"))?;
        Ok((s, is_float))
    }

    fn build_number<'py>(
        &mut self,
        py: Python<'py>,
    ) -> Result<Bound<'py, PyAny>, SerializationError> {
        let (slice, is_float) = self.parse_number_slice(py)?;
        if is_float {
            let f: f64 = slice.parse().map_err(|_| Self::err(py, "invalid number"))?;
            return Ok(PyFloat::new(py, f).into_any());
        }
        if let Ok(i) = slice.parse::<i64>() {
            return i
                .into_py_any(py)
                .map(|p| p.into_bound(py))
                .map_err(|e| SerializationError::from_pyerr(py, &e));
        }
        py.import("builtins")
            .and_then(|b| b.getattr("int"))
            .and_then(|int| int.call1((slice,)))
            .map_err(|e| SerializationError::from_pyerr(py, &e))
    }

    fn enter(&mut self, py: Python<'_>) -> Result<(), SerializationError> {
        self.depth += 1;
        if self.depth > MAX_DEPTH {
            return Err(Self::err(py, "nesting too deep"));
        }
        Ok(())
    }

    const fn leave(&mut self) {
        self.depth -= 1;
    }

    /// Drive a JSON object: handle `{`, `}`, commas, the empty case, nesting depth, and syntax
    /// errors here once; `on_member` is called with the parser positioned at each member's value
    /// (after `key` and `:`).
    pub fn iter_object<F>(
        &mut self,
        py: Python<'_>,
        mut on_member: F,
    ) -> Result<(), SerializationError>
    where
        F: FnMut(&mut Self, &str) -> Result<(), SerializationError>,
    {
        self.enter(py)?;
        self.expect(py, b'{')?;
        if self.peek_byte() == Some(b'}') {
            self.bump();
        } else {
            loop {
                let key = self.parse_string_raw(py)?;
                self.expect(py, b':')?;
                on_member(self, &key)?;
                match self.peek_byte() {
                    Some(b',') => self.bump(),
                    Some(b'}') => {
                        self.bump();
                        break;
                    }
                    _ => return Err(Self::err(py, "expected ',' or '}'")),
                }
            }
        }
        self.leave();
        Ok(())
    }

    /// Drive a JSON array: handle `[`, `]`, commas, the empty case, nesting depth, and syntax
    /// errors here once; `on_item` is called with the parser positioned at each item.
    pub fn iter_array<F>(
        &mut self,
        py: Python<'_>,
        mut on_item: F,
    ) -> Result<(), SerializationError>
    where
        F: FnMut(&mut Self) -> Result<(), SerializationError>,
    {
        self.enter(py)?;
        self.expect(py, b'[')?;
        if self.peek_byte() == Some(b']') {
            self.bump();
        } else {
            loop {
                on_item(self)?;
                match self.peek_byte() {
                    Some(b',') => self.bump(),
                    Some(b']') => {
                        self.bump();
                        break;
                    }
                    _ => return Err(Self::err(py, "expected ',' or ']'")),
                }
            }
        }
        self.leave();
        Ok(())
    }

    /// Parse the next JSON value into the Python object that `json.loads` would build.
    pub fn parse_to_pyobject<'py>(
        &mut self,
        py: Python<'py>,
    ) -> Result<Bound<'py, PyAny>, SerializationError> {
        self.skip_ws();
        match self.peek(py)? {
            b'"' => {
                let s = self.parse_string_raw(py)?;
                Ok(PyString::new(py, &s).into_any())
            }
            b'{' => {
                let dict = PyDict::new(py);
                self.iter_object(py, |s, key| {
                    let value = s.parse_to_pyobject(py)?;
                    dict.set_item(PyString::new(py, key), value)
                        .map_err(|e| SerializationError::from_pyerr(py, &e))
                })?;
                Ok(dict.into_any())
            }
            b'[' => {
                let list = PyList::empty(py);
                self.iter_array(py, |s| {
                    let value = s.parse_to_pyobject(py)?;
                    list.append(value)
                        .map_err(|e| SerializationError::from_pyerr(py, &e))
                })?;
                Ok(list.into_any())
            }
            b't' => {
                self.lit(py, "true")?;
                Ok(PyBool::new(py, true).to_owned().into_any())
            }
            b'f' => {
                self.lit(py, "false")?;
                Ok(PyBool::new(py, false).to_owned().into_any())
            }
            b'n' => {
                self.lit(py, "null")?;
                Ok(py.None().into_bound(py))
            }
            b'N' => {
                self.lit(py, "NaN")?;
                Ok(PyFloat::new(py, f64::NAN).into_any())
            }
            b'I' => {
                self.lit(py, "Infinity")?;
                Ok(PyFloat::new(py, f64::INFINITY).into_any())
            }
            b'-' if self.d.get(self.i + 1) == Some(&b'I') => {
                self.i += 1;
                self.lit(py, "Infinity")?;
                Ok(PyFloat::new(py, f64::NEG_INFINITY).into_any())
            }
            b'-' | b'0'..=b'9' => self.build_number(py),
            _ => Err(Self::err(py, "unexpected token")),
        }
    }

    pub fn skip_value(&mut self, py: Python<'_>) -> Result<(), SerializationError> {
        self.skip_ws();
        match self.peek(py)? {
            b'"' => {
                self.parse_string_raw(py)?;
            }
            b'{' => self.iter_object(py, |s, _key| s.skip_value(py))?,
            b'[' => self.iter_array(py, |s| s.skip_value(py))?,
            b't' => self.lit(py, "true")?,
            b'f' => self.lit(py, "false")?,
            b'n' => self.lit(py, "null")?,
            b'N' => self.lit(py, "NaN")?,
            b'I' => self.lit(py, "Infinity")?,
            b'-' if self.d.get(self.i + 1) == Some(&b'I') => {
                self.i += 1;
                self.lit(py, "Infinity")?;
            }
            b'-' | b'0'..=b'9' => {
                self.parse_number_slice(py)?;
            }
            _ => return Err(Self::err(py, "unexpected token")),
        }
        Ok(())
    }
}
