# Change: Define core and adapter boundaries for registry and index lifecycle

## Why
`rlm-core` is intended to generalize the `rlm-tools` / `rlm-tools-bsl` model across multiple languages, but the boundary between shared platform concerns and language-specific concerns is not yet defined. Without an explicit architecture decision, the future `core` risks inheriting BSL-specific assumptions or pushing duplicated lifecycle logic into every adapter.

## What Changes
- Define the shared `core` responsibility for workspace/project registry and index lifecycle orchestration.
- Define the `adapter` responsibility for language-specific repository detection, index build/read logic, helper registration, and schema extensions.
- Standardize capability negotiation so adapters can declare whether they support prebuilt indexes, incremental updates, and adapter-specific indexed features.
- Keep registry usage optional so the runtime can operate both by direct filesystem path and by registered project/workspace identifier.

## Impact
- Affected specs: `core-adapter-boundaries`
- Affected code: future `rlm_core.runtime`, `rlm_core.index`, `rlm_core.adapters`, MCP tool routing, and BSL adapter migration work
