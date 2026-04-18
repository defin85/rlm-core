# Architecture Draft

## Top-level shape

The repository is intended to evolve into three stable layers:

1. `rlm_core.runtime`
   Session manager, sandbox execution, usage tracking, transport-agnostic orchestration.
2. `rlm_core.index`
   Generic repository index, schema management, refresh/update flow, read APIs.
3. `rlm_core.adapters`
   Per-language discovery, parsing, symbol extraction, call extraction, and specialized helper registration.

## Adapter contract

Each language adapter should eventually provide:

- `detect(path) -> bool`
- `describe_repo(path) -> RepoDescriptor`
- `build_index(path, writer) -> None`
- `register_helpers(context) -> dict[str, callable]`
- `build_strategy(query, context) -> str`

## Target generic entities

The core index should focus on generic entities first:

- files
- symbols
- definitions
- references
- calls
- imports
- diagnostics

Language-specific metadata should live in adapter-owned tables or JSON payloads.

## Expected adapter strategy

- `bsl`: migrate current `rlm-tools-bsl` indexing and helper model into adapter form.
- `typescript`: AST + language service hybrid.
- `go`: AST + `gopls` integration.
- `rust`: AST + `rust-analyzer` integration.
- `java`: AST + `jdtls` integration.

## Non-goals for the first phase

- Full cross-language symbol linking
- Remote code indexing service
- Embedding-based semantic search as a hard dependency
