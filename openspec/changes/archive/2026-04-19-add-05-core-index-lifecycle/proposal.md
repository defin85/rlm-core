# Change: Add core index lifecycle

## Why
Once the generic index model exists, the repository needs a shared lifecycle for build, update, drop, info, and status/check operations. This lifecycle must be core-owned so it does not fragment across adapters.

## What Changes
- Implement the shared `IndexManager` orchestration surface.
- Add background build/update orchestration, locking, and status reporting.
- Support lifecycle operation in path-only mode before registry-backed mode is added.

## Impact
- Affected specs: `core-index-lifecycle`
- Affected code: future `IndexManager`, job orchestration, index status APIs, lifecycle tests
