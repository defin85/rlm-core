# Change: Define sequential implementation roadmap

## Why
`rlm-core` now has project context and an architecture decision for `core` versus `adapter` boundaries, but it does not yet have an agreed implementation sequence. Without a staged roadmap, there is a high risk of overdesigning the generic index too early, coupling the shared core to BSL migration details, or starting public API work before the core runtime is stable.

## What Changes
- Define the ordered sequence of implementation changes for `rlm-core`.
- Group the roadmap into execution phases with explicit gates.
- Record dependency rules so that later changes do not start before their architectural prerequisites are in place.
- Create a planning baseline that future implementation work can follow or refine explicitly.

## Impact
- Affected specs: `implementation-roadmap`
- Affected change planning: `add-01-*` through `add-13-*`
