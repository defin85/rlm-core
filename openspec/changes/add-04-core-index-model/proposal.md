# Change: Add core index model

## Why
Before any adapter can provide a production-grade prebuilt index, `rlm-core` needs a shared index model for the generic entities it will own. Without this model, every adapter will invent incompatible storage and read semantics.

## What Changes
- Define the generic index entities owned by the shared core.
- Define write/read contracts for generic index storage.
- Keep adapter-specific metadata outside the shared core entity set.

## Impact
- Affected specs: `core-index-model`
- Affected code: future `rlm_core.index` entities, readers, writers, storage contract tests
