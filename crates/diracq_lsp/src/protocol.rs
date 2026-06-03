//! Minimal LSP base-protocol framing over stdio (dependency-free).
//!
//! LSP messages are `Content-Length: N\r\n\r\n<N bytes of JSON>`. We implement
//! just enough to read and write those frames with `serde_json::Value` bodies,
//! so the server has no heavy `lsp-types`/`tower-lsp` dependency while the
//! protocol surface is small (Workstream B may swap in a richer crate later).

use std::io::{BufRead, Write};

use serde_json::Value;

/// Read one LSP message. Returns `Ok(None)` on clean EOF.
pub fn read_message<R: BufRead>(reader: &mut R) -> anyhow::Result<Option<Value>> {
    let mut content_length: Option<usize> = None;
    loop {
        let mut line = String::new();
        let n = reader.read_line(&mut line)?;
        if n == 0 {
            return Ok(None); // EOF
        }
        let trimmed = line.trim_end_matches(['\r', '\n']);
        if trimmed.is_empty() {
            break; // end of headers
        }
        if let Some(rest) = trimmed.strip_prefix("Content-Length:") {
            content_length = Some(rest.trim().parse()?);
        }
        // Other headers (Content-Type) are ignored.
    }
    let len =
        content_length.ok_or_else(|| anyhow::anyhow!("LSP frame missing Content-Length header"))?;
    let mut buf = vec![0u8; len];
    reader.read_exact(&mut buf)?;
    Ok(Some(serde_json::from_slice(&buf)?))
}

/// Write one LSP message with the required `Content-Length` header.
pub fn write_message<W: Write>(writer: &mut W, message: &Value) -> anyhow::Result<()> {
    let body = serde_json::to_vec(message)?;
    write!(writer, "Content-Length: {}\r\n\r\n", body.len())?;
    writer.write_all(&body)?;
    writer.flush()?;
    Ok(())
}

/// Convert a byte offset into an LSP `{line, character}` position.
///
/// Character is counted in UTF-16 code units per the spec; for the ASCII-heavy
/// Guppy surface this matches scalar counts, and we compute it correctly for
/// non-ASCII too.
pub fn offset_to_position(src: &str, offset: usize) -> (u32, u32) {
    let mut line = 0u32;
    let mut col = 0u32;
    for (i, ch) in src.char_indices() {
        if i >= offset {
            break;
        }
        if ch == '\n' {
            line += 1;
            col = 0;
        } else {
            col += ch.len_utf16() as u32;
        }
    }
    (line, col)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    fn roundtrip_frame() {
        let msg = serde_json::json!({"jsonrpc":"2.0","id":1,"method":"initialize"});
        let mut buf = Vec::new();
        write_message(&mut buf, &msg).unwrap();
        let mut cursor = Cursor::new(buf);
        let got = read_message(&mut cursor).unwrap().unwrap();
        assert_eq!(got["method"], "initialize");
    }

    #[test]
    fn eof_returns_none() {
        let mut cursor = Cursor::new(Vec::new());
        assert!(read_message(&mut cursor).unwrap().is_none());
    }

    #[test]
    fn position_mapping() {
        let src = "ab\ncd\n";
        assert_eq!(offset_to_position(src, 0), (0, 0));
        assert_eq!(offset_to_position(src, 1), (0, 1));
        assert_eq!(offset_to_position(src, 3), (1, 0)); // first char of line 1
        assert_eq!(offset_to_position(src, 4), (1, 1));
    }
}
