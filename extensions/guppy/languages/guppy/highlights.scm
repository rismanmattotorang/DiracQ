; tree-sitter-guppy highlights (extends the Python base).
; Guppy is Python with decorators and a linear type discipline; this query adds
; the Guppy-specific surface: the @guppy decorator family, qubit/array/angle
; types, and the quantum builtins.

; @guppy decorator family
(decorator (identifier) @function.macro
  (#match? @function.macro "guppy"))

; Guppy builtin types
(type (identifier) @type.builtin
  (#any-of? @type.builtin "qubit" "array" "angle"))

; Quantum builtins
(call function: (identifier) @function.builtin
  (#any-of? @function.builtin "h" "cx" "rz" "measure"))

; Annotations such as @owned / comptime
((identifier) @keyword
  (#any-of? @keyword "owned" "comptime"))

; Fall back to the Python base for everything else.
(comment) @comment
(string) @string
(integer) @number
(float) @number
