//! Length-prefixed JSON framing for the internal sidecar/worker bridges.
//!
//! Frames are a 4-byte big-endian length followed by a UTF-8 JSON body. This is
//! the framing the Rust core uses to talk to the Python sidecar and the
//! `guppylang` worker (distinct from the editor-facing LSP `Content-Length`
//! framing). Kept here so every crate that speaks the bridge shares one
//! implementation.

use std::io::{Read, Write};

use serde_json::Value;

/// Write one length-prefixed JSON frame.
pub fn write_frame<W: Write>(w: &mut W, msg: &Value) -> anyhow::Result<()> {
    let body = serde_json::to_vec(msg)?;
    w.write_all(&(body.len() as u32).to_be_bytes())?;
    w.write_all(&body)?;
    w.flush()?;
    Ok(())
}

/// Read one length-prefixed JSON frame. Returns `Ok(None)` on clean EOF.
pub fn read_frame<R: Read>(r: &mut R) -> anyhow::Result<Option<Value>> {
    let mut len = [0u8; 4];
    match r.read_exact(&mut len) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => return Ok(None),
        Err(e) => return Err(e.into()),
    }
    let n = u32::from_be_bytes(len) as usize;
    let mut body = vec![0u8; n];
    r.read_exact(&mut body)?;
    Ok(Some(serde_json::from_slice(&body)?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::io::Cursor;

    #[test]
    fn roundtrip_then_eof() {
        let mut buf = Vec::new();
        write_frame(&mut buf, &json!({"method": "x"})).unwrap();
        let mut cur = Cursor::new(buf);
        assert_eq!(read_frame(&mut cur).unwrap().unwrap()["method"], "x");
        assert!(read_frame(&mut cur).unwrap().is_none());
    }
}
