# Change: Add generic helper baseline

## Why
The walking skeleton alone does not provide useful repository exploration. `rlm-core` needs a small generic helper surface that matches the upstream `rlm-tools` value proposition before adapter-specific helpers are introduced.

## What Changes
- Add a baseline set of generic repository helpers such as file reads, grep, glob, and tree listing.
- Ensure helper outputs remain compact and sandbox-oriented rather than dumping uncontrolled raw data.
- Keep the helper set language-agnostic and path-based.

## Impact
- Affected specs: `generic-helper-baseline`
- Affected code: future generic helper registry, sandbox helper injection, helper tests
