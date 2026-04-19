# Change: Add adapter SPI and selection

## Why
After the runtime and generic helper baseline exist, the next architectural prerequisite is a stable adapter contract. Without it, every language migration would reintroduce branching and coupling into the shared runtime.

## What Changes
- Define the adapter SPI for detection, repository description, helper registration, and index hooks.
- Add adapter registry/selection logic for path-based sessions.
- Introduce explicit adapter capability declaration.

## Impact
- Affected specs: `adapter-selection`
- Affected code: future `rlm_core.adapters`, runtime adapter registry, capability negotiation
