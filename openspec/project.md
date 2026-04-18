# Project Context

## Purpose
`rlm-core` is a multilingual indexed RLM core for MCP-based repository analysis. The project exists to generalize the proven exploration model from `rlm-tools` and `rlm-tools-bsl`: agents should inspect repositories through a sandboxed helper/runtime layer, optionally accelerated by a local structural index, instead of dumping raw files into model context.

## Tech Stack
- Python 3.11+
- Hatchling packaging
- Pytest for tests
- Ruff for linting/format-oriented checks
- OpenSpec for architecture and capability change management
- Beads (`bd`) for issue/task tracking

## Project Conventions

### Code Style
- Follow the existing Python style in the repository and keep changes minimal and explicit.
- Prefer typed, readable APIs over clever abstractions.
- Use ASCII unless a file already requires Unicode.
- Fix root causes instead of layering workarounds.
- Read relevant files before editing and keep refactors scoped to the task.

### Architecture Patterns
- Target architecture is `core + adapters`.
- `rlm_core.runtime` owns session management, sandbox execution, usage tracking, transport-agnostic orchestration, and the external MCP-facing lifecycle.
- `rlm_core.index` owns generic index abstractions and lifecycle orchestration, while language-specific index implementation remains in adapters.
- `rlm_core.adapters` owns per-language detection, parsing, symbol extraction, helper registration, and adapter-specific indexed features.
- Generic entities come first: `files`, `symbols`, `definitions`, `references`, `calls`, `imports`, `diagnostics`.
- Language-specific metadata belongs in adapter-owned extensions rather than in the shared core schema.

### Testing Strategy
- Run the smallest relevant verification set for every change.
- Use `pytest` for Python behavior and contract tests.
- Validate OpenSpec artifacts with `openspec validate --strict --no-interactive`.
- As adapter boundaries are implemented, add focused tests for path-only operation, registry-backed operation, and capability negotiation.
- Do not mark work complete if behavior is deferred into TODOs or unchecked assumptions.

### Git Workflow
- Use OpenSpec proposals for new capabilities, architecture changes, and other non-trivial behavior changes before implementation.
- Use Beads for task tracking instead of markdown TODO tracking.
- Keep commits focused and factual.
- The repository currently uses `main`; no additional branching workflow is documented yet.

## Domain Context
- RLM here means repository-level machine-coding: the agent explores code through helper calls and sandbox execution rather than through full-repo prompt stuffing.
- The project is inspired by upstream `rlm-tools` and uses `rlm-tools-bsl` as the first concrete migration reference.
- The local index is an accelerator and source of structured answers, not a mandatory remote RAG service.
- The first migration target is BSL, but the long-term goal is a reusable multilingual runtime that also supports mainstream languages such as TypeScript, Go, Rust, and Java.

## Important Constraints
- Do not bake BSL-specific assumptions into the shared core.
- Preserve the lightweight direct-path workflow from `rlm-tools`; registry-backed mode is important but must remain optional.
- Adapter capabilities may differ; the core must not assume that every language supports prebuilt indexes or incremental updates.
- Phase 1 explicitly excludes full cross-language symbol linking, remote indexing services, and embedding-based search as a hard dependency.
- Prefer a stable external API with internal capability negotiation over language-specific MCP surface area.

## External Dependencies
- Upstream reference: `defin85/rlm-tools`
- Migration reference and first adapter source: local `rlm-tools-bsl`
- MCP clients/hosts that will call the runtime
- Planned adapter-side integrations may include language-specific tooling such as `gopls`, `rust-analyzer`, `jdtls`, or comparable parser/indexer components, but these are adapter concerns rather than shared core requirements
