# Change: Add cross-adapter hardening

## Why
After the second adapter is in place, the remaining work is to remove implicit first-adapter assumptions and harden the repository as a genuinely multilingual core with explicit capability boundaries.

## What Changes
- Harden capability negotiation and fallback behavior across adapters.
- Remove or isolate remaining BSL-first assumptions in shared code and docs.
- Align tests, documentation, and product semantics across adapters.

## Impact
- Affected specs: `cross-adapter-hardening`
- Affected code: shared runtime hardening, capability matrix behavior, cross-adapter tests and docs
