# Architecture

## Stable layers

The repository now has three stable shared layers:

1. `rlm_core.runtime`
   Session lifecycle, workspace resolution, adapter selection, sandbox execution, and mutation policy enforcement.
2. `rlm_core.index`
   Shared lifecycle orchestration for build/update/drop/info/check, background jobs, locking, and uniform unsupported semantics.
3. `rlm_core.adapters`
   Language-owned repository detection, descriptor generation, helper registration, strategy text, and optional index hooks.

## Current adapter SPI

Each adapter integrates through the shared SPI:

- `detect(workspace) -> bool`
- `describe_repo(workspace) -> RepositoryDescriptor`
- `register_helpers(context) -> dict[str, callable]`
- `build_strategy(query, context) -> str`
- `get_index_hooks() -> IndexHooks | None`

`get_index_hooks()` is optional by design. Live-only adapters can participate in the shared runtime without implementing prebuilt index lifecycle support.

## Capability model

Shared behavior is driven by `IndexCapabilityMatrix`:

- `generic` direct-path mode exposes shared helpers only and no adapter lifecycle actions.
- `bsl` supports live workflows plus adapter-owned prebuilt snapshots and advanced metadata snapshots.
- `go` supports live workflows only; lifecycle actions are surfaced as explicit `unsupported`.

This is intentional. Callers should rely on shared capability semantics rather than assuming every adapter behaves like the first indexed adapter.

## Generic index model

The core index model stays language-neutral:

- files
- symbols
- definitions
- references
- calls
- imports
- diagnostics

Language-specific metadata stays adapter-owned inside adapter snapshots or adapter-specific payloads layered over the generic contracts.

## Public surface

The stable external surface lives in `rlm_core.public_api` and `rlm_core.cli`.

Public tools:

- `rlm_projects`
- `rlm_start`
- `rlm_execute`
- `rlm_end`
- `rlm_index`
- `rlm_index_job`
- `rlm_wait_for_index_job`

All lifecycle responses use shared status shapes. Unsupported actions must return structured `unsupported` data with explicit reasons and supported action lists instead of adapter-selection failures.

## Non-goals

- Cross-language symbol linking
- Remote indexing services
- Mandatory embedding search
