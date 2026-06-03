//! The DiracQ Guppy LSP server loop.
//!
//! Implements the minimal lifecycle the editor needs for M1: `initialize` →
//! `initialized` → `textDocument/{didOpen,didChange,didClose}` → diagnostics
//! published via `textDocument/publishDiagnostics`, plus `shutdown`/`exit`.
//!
//! Documents are synced in full (`TextDocumentSyncKind.Full`) — simplest and
//! plenty fast for the buffer sizes Guppy kernels occupy. Each change runs the
//! injected [`GuppyAnalysis`] and republishes diagnostics. Workstream B swaps
//! the heuristic analyzer for the debounced `guppylang` worker without changing
//! this loop.

use std::collections::HashMap;
use std::io::{BufRead, Write};

use serde_json::{json, Value};

use crate::protocol::{offset_to_position, read_message, write_message};
use crate::{GuppyAnalysis, Severity};

/// Run the server until the client sends `exit` (or stdio reaches EOF).
pub fn run<A, R, W>(analysis: A, reader: &mut R, writer: &mut W) -> anyhow::Result<()>
where
    A: GuppyAnalysis,
    R: BufRead,
    W: Write,
{
    let mut docs: HashMap<String, String> = HashMap::new();
    let mut shutting_down = false;

    while let Some(msg) = read_message(reader)? {
        let method = msg.get("method").and_then(Value::as_str).unwrap_or("");
        let id = msg.get("id").cloned();

        match method {
            "initialize" => {
                if let Some(id) = id {
                    write_message(writer, &initialize_result(id))?;
                }
            }
            "initialized" => { /* notification, no reply */ }
            "textDocument/didOpen" => {
                if let Some((uri, text)) = open_params(&msg) {
                    docs.insert(uri.clone(), text.clone());
                    publish_diagnostics(&analysis, writer, &uri, &text)?;
                }
            }
            "textDocument/didChange" => {
                if let Some((uri, text)) = change_params(&msg) {
                    docs.insert(uri.clone(), text.clone());
                    publish_diagnostics(&analysis, writer, &uri, &text)?;
                }
            }
            "textDocument/didClose" => {
                if let Some(uri) = msg
                    .pointer("/params/textDocument/uri")
                    .and_then(Value::as_str)
                {
                    docs.remove(uri);
                }
            }
            "shutdown" => {
                shutting_down = true;
                if let Some(id) = id {
                    write_message(writer, &json!({"jsonrpc":"2.0","id":id,"result":null}))?;
                }
            }
            "exit" => break,
            _ => {
                // Unknown request: respond with MethodNotFound so the client
                // isn't left waiting. Unknown notifications are ignored.
                if let Some(id) = id {
                    write_message(
                        writer,
                        &json!({
                            "jsonrpc":"2.0","id":id,
                            "error":{"code":-32601,"message":format!("method not found: {method}")}
                        }),
                    )?;
                }
            }
        }
    }

    let _ = shutting_down;
    Ok(())
}

fn initialize_result(id: Value) -> Value {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": {
            "capabilities": {
                // 1 = Full document sync.
                "textDocumentSync": 1,
                "hoverProvider": true,
                "diagnosticProvider": { "interFileDependencies": false, "workspaceDiagnostics": false }
            },
            "serverInfo": { "name": "diracq-guppy-lsp", "version": env!("CARGO_PKG_VERSION") }
        }
    })
}

fn open_params(msg: &Value) -> Option<(String, String)> {
    let uri = msg
        .pointer("/params/textDocument/uri")?
        .as_str()?
        .to_string();
    let text = msg
        .pointer("/params/textDocument/text")?
        .as_str()?
        .to_string();
    Some((uri, text))
}

fn change_params(msg: &Value) -> Option<(String, String)> {
    let uri = msg
        .pointer("/params/textDocument/uri")?
        .as_str()?
        .to_string();
    // Full sync: the last content change holds the entire document text.
    let changes = msg.pointer("/params/contentChanges")?.as_array()?;
    let text = changes.last()?.get("text")?.as_str()?.to_string();
    Some((uri, text))
}

fn publish_diagnostics<A: GuppyAnalysis, W: Write>(
    analysis: &A,
    writer: &mut W,
    uri: &str,
    text: &str,
) -> anyhow::Result<()> {
    let diags = analysis.check(uri, text).unwrap_or_default();
    let lsp_diags: Vec<Value> = diags
        .iter()
        .map(|d| {
            let (sl, sc) = offset_to_position(text, d.range.0);
            let (el, ec) = offset_to_position(text, d.range.1);
            json!({
                "range": {
                    "start": {"line": sl, "character": sc},
                    "end":   {"line": el, "character": ec}
                },
                "severity": severity_code(d.severity),
                "source": "diracq-guppy",
                "message": d.message
            })
        })
        .collect();

    write_message(
        writer,
        &json!({
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": { "uri": uri, "diagnostics": lsp_diags }
        }),
    )
}

fn severity_code(s: Severity) -> i32 {
    match s {
        Severity::Error => 1,
        Severity::Warning => 2,
        Severity::Information => 3,
        Severity::Hint => 4,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::analyzer::HeuristicAnalyzer;
    use crate::protocol::write_message;
    use std::io::Cursor;

    /// Drive the server with an initialize + didOpen of a buggy program and
    /// assert it answers initialize and publishes a use-after-measure diagnostic.
    #[test]
    fn initialize_and_publish_diagnostics() {
        let mut input = Vec::new();
        write_message(
            &mut input,
            &json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}),
        )
        .unwrap();
        write_message(
            &mut input,
            &json!({
                "jsonrpc":"2.0","method":"textDocument/didOpen",
                "params":{"textDocument":{
                    "uri":"file:///bell.guppy",
                    "languageId":"Guppy","version":1,
                    "text":"q = qubit()\nmeasure(q)\nh(q)\n"
                }}
            }),
        )
        .unwrap();
        write_message(&mut input, &json!({"jsonrpc":"2.0","method":"exit"})).unwrap();

        let mut reader = Cursor::new(input);
        let mut out: Vec<u8> = Vec::new();
        run(HeuristicAnalyzer, &mut reader, &mut out).unwrap();

        let text = String::from_utf8(out).unwrap();
        assert!(text.contains("\"serverInfo\""), "missing initialize result");
        assert!(text.contains("publishDiagnostics"), "missing diagnostics");
        assert!(
            text.contains("use-after-measure"),
            "missing the expected diagnostic"
        );
    }
}
