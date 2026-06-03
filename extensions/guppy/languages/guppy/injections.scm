; tree-sitter-guppy injections.
; Guppy embeds Python; docstrings and embedded fragments are highlighted as
; Python so the base language tooling applies inside Guppy kernels.

((string) @injection.content
  (#set! injection.language "python"))
