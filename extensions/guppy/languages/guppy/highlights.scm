; Guppy highlights — layered on the upstream tree-sitter-python parse tree.
; Guppy is Python syntactically, so node types below are tree-sitter-python's;
; these queries add the Guppy-specific surface (decorators, quantum types and
; builtins) on top of ordinary Python highlighting.

; ── The @guppy decorator family ───────────────────────────────────────────
; @guppy
(decorator (identifier) @function.macro
  (#match? @function.macro "^guppy$"))
; @guppy.declare / @guppy.struct / etc.
(decorator (attribute object: (identifier) @function.macro)
  (#match? @function.macro "^guppy$"))

; ── Guppy builtin types in annotations ─────────────────────────────────────
; e.g. `q: qubit`, `xs: array[qubit, n]`, `theta: angle`
(type (identifier) @type.builtin
  (#any-of? @type.builtin "qubit" "array" "angle" "bool" "int" "float"))
(type (subscript value: (identifier) @type.builtin)
  (#any-of? @type.builtin "array"))

; ── Quantum builtin operations ─────────────────────────────────────────────
(call function: (identifier) @function.builtin
  (#any-of? @function.builtin
    "h" "x" "y" "z" "s" "t" "sdg" "tdg" "cx" "cz"
    "rx" "ry" "rz" "measure" "reset" "qubit" "discard"))

; ── @owned / comptime annotations ──────────────────────────────────────────
((identifier) @keyword
  (#any-of? @keyword "owned" "comptime"))

; ── Generic Python fallbacks ───────────────────────────────────────────────
(function_definition name: (identifier) @function)
(call function: (identifier) @function)
(comment) @comment
(string) @string
(integer) @number
(float) @number
[ "def" "return" "if" "else" "elif" "for" "while" "with" "import" "from" ] @keyword
