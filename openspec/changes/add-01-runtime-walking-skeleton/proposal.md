# Change: Add runtime walking skeleton

## Why
`rlm-core` needs a minimal end-to-end runtime loop before adapter, index, and public API work can be validated. Without a walking skeleton, later changes would be designed against abstractions that have never executed together.

## What Changes
- Introduce the minimal runtime components for session creation, sandbox execution, and session teardown.
- Support direct-path repository exploration without registry or prebuilt index requirements.
- Preserve the upstream `rlm-tools` exploration loop as the initial behavioral baseline.

## Impact
- Affected specs: `runtime-walking-skeleton`
- Affected code: future `rlm_core.runtime`, session lifecycle, sandbox runtime entrypoints
