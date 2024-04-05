Find isomorphisms (blocks of code with the same structure) across repos and
languages.

Currently only tested with Python and Rust, but uses tree-sitter
(https://tree-sitter.github.io/tree-sitter/) so the approach should be general.

Future work:

- Improve cross-language comparisons by normalizing tree-sitter node names.
- Add more languages.
- Find some interesting isomorphisms.
