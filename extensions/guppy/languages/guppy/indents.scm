; Guppy indents — tree-sitter-python node types. Zed uses these to decide
; auto-indentation; Python's block structure drives Guppy's the same way.
(block) @indent

[
  (function_definition)
  (class_definition)
  (if_statement)
  (for_statement)
  (while_statement)
  (with_statement)
] @indent
