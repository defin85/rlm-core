# Change: Add quality, evals, and safety gates

## Why
`rlm-core` aims to be token-efficient, safe, and adapter-extensible, but those claims need measurable evidence. Once the public surface exists, the repository needs explicit evals, benchmarks, and sandbox hardening gates.

## What Changes
- Add evaluation fixtures and benchmark workflows for runtime and adapter behavior.
- Add safety and regression tests for sandboxing, timeouts, and lifecycle behavior.
- Make context-efficiency and latency claims measurable rather than anecdotal.

## Impact
- Affected specs: `quality-evals-safety`
- Affected code: future test fixtures, benchmark harnesses, safety checks, evaluation scripts
