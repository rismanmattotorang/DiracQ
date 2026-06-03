//! DiracQ Guppy language extension (§18.2, Workstream A — WASM, no fork).
//!
//! The LSP adapter is the only procedural code, and it must respect the WASM
//! sandbox: it locates the `diracq-guppy-lsp` binary through the API's
//! `Worktree` (never `std::env`), since `std::env::var` and `cfg` do not behave
//! as in native code inside the wasm32-wasip2 sandbox.

use zed_extension_api::{self as zed, Command, LanguageServerId, Result, Worktree};

struct GuppyExtension;

impl zed::Extension for GuppyExtension {
    fn new() -> Self {
        GuppyExtension
    }

    fn language_server_command(
        &mut self,
        _id: &LanguageServerId,
        worktree: &Worktree, // sandbox-safe host access
    ) -> Result<Command> {
        // Locate the DiracQ Guppy LSP on PATH via the worktree, never std::env.
        let path = worktree
            .which("diracq-guppy-lsp")
            .ok_or_else(|| "diracq-guppy-lsp not found on PATH".to_string())?;
        Ok(Command {
            command: path,
            args: vec!["--stdio".into()],
            env: vec![],
        })
    }
}

zed::register_extension!(GuppyExtension);
