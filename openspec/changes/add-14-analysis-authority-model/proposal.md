# Change: Add analysis authority model

## Why
`rlm-core` already exposes stable runtime, lifecycle, and cross-adapter capability semantics, but it still does not tell callers how much to trust analysis answers. Today a caller can see adapter identity and helper names, but it cannot distinguish textual exploration, heuristic language parsing, syntactic structure, semantic resolution, or authoritative toolchain-backed answers through a shared contract.

Without an explicit authority model, agents can over-trust approximate answers such as call chains, references, and symbol relationships. This is now the main architectural gap between the current helper/runtime surface and a reliable multilingual analysis product.

## What Changes
- Add a shared analysis authority model that distinguishes textual, heuristic, syntactic, semantic, and authoritative analysis levels.
- Add adapter-neutral contracts for adapter-owned analysis providers and backend provenance.
- Require analysis helpers that make structural or semantic claims to distinguish approximate results from resolved results.
- Extend the public/runtime surface to expose machine-readable authority metadata instead of forcing callers to infer trust from adapter names and strategy text.
- Add authority-aware quality gates so the repository can test for overclaiming, not only workflow liveness.

## Impact
- Affected specs: `analysis-authority-model`, `core-adapter-boundaries`, `public-api-surface`, `cross-adapter-hardening`, `quality-evals-safety`
- Affected code: `src/rlm_core/adapters/contracts.py`, `src/rlm_core/runtime/service.py`, `src/rlm_core/public_api.py`, `src/rlm_core/evals.py`, adapter implementations, adapter contract tests
