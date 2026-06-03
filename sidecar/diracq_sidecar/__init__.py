"""DiracQ Python sidecar (semi-trusted, sandboxed — Table 6).

Hosts the heavy quantum/ML work off the editor's UI thread, behind a JSON-RPC
2.0 bridge addressed by the trusted Rust core. The sidecar holds no secrets and
reaches the network only through an allowlist; secrets are injected per-request
by the core (§13.3).
"""

__version__ = "0.1.0"
