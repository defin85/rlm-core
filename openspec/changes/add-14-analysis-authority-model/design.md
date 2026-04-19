## Context

The current architecture separates shared runtime/index orchestration from adapter-owned language behavior, but the contract stops at helper registration, strategy text, and optional index hooks. This works for liveness and basic navigation, yet it leaves one critical question unanswered for agents: how trustworthy is any given analysis answer?

This gap is visible today:

- `generic` mode provides textual exploration only.
- `go` currently exposes language-aware live helpers built on heuristic parsing.
- `bsl` combines live parsing, indexed snapshots, and XML-backed metadata extraction.

All three modes are useful, but they do not have the same trust characteristics. The architecture needs an explicit authority model before more adapters and deeper semantic features are added.

## Goals / Non-Goals

- Goals:
  - Define a shared vocabulary for trust and authority across adapters.
  - Keep semantic backends adapter-owned rather than moving language semantics into core.
  - Expose machine-readable trust metadata to agents and external callers.
  - Prevent approximate helpers from presenting their results as resolved truth.
  - Extend quality gates from workflow liveness to authority-aware correctness.
- Non-Goals:
  - Implement full semantic backends for every language in this change.
  - Require every adapter to support semantic or authoritative analysis immediately.
  - Introduce cross-language symbol linking.
  - Replace adapter-specific helper surfaces with one universal query language in a single step.

## Decisions

- Decision: authority is a first-class shared contract.
  - The runtime and public API should expose analysis trust explicitly instead of expecting callers to infer it from helper names, adapter IDs, or strategy text.
- Decision: semantic backends remain adapter-owned.
  - Core should orchestrate authority and provenance, but each adapter should own how semantic or authoritative analysis is obtained.
- Decision: relationship claims must distinguish possible versus resolved results.
  - Helpers that report callers, callees, references, implementations, or similar analysis claims must mark approximate results clearly.
- Decision: provenance must accompany higher-value analysis results.
  - Backend identity, backend kind, freshness or staleness, and evidence references are necessary for auditability.
- Decision: evals must test overclaiming.
  - Workflow success is not enough; the repository should fail changes that silently upgrade heuristic answers into resolved ones.

## Risks / Trade-offs

- More metadata can make helper payloads and public responses noisier.
  - Mitigation: keep the authority vocabulary small and standardize reusable envelope fields.
- Retrofitting existing helpers may create a temporary mixed world.
  - Mitigation: stage the rollout through session metadata first, then helper claim envelopes, then stricter eval gates.
- Different languages may not map cleanly to one trust ladder.
  - Mitigation: standardize the top-level levels, but allow adapter-owned backend kinds and evidence details.
- There is a risk of inventing semantic confidence without a real backend.
  - Mitigation: require explicit provider declarations and treat the absence of such providers as heuristic-only capability.

## Migration Plan

1. Add authority and provenance vocabulary plus adapter-neutral provider declarations.
2. Surface analysis authority in session/public metadata so agents can route themselves correctly before calling helpers.
3. Introduce structured claim semantics for relationship helpers, including possible versus resolved classification.
4. Update evals and tests to gate on authority correctness.
5. Retrofit adapters incrementally, starting with the current `generic`, `go`, and `bsl` modes.

## Open Questions

- Should helper results use one shared `_analysis` metadata envelope or a more explicit per-helper schema family?
- Which fields must be mandatory in every claim, and which can remain adapter-specific extensions?
- How much of this authority model should be reflected in the generic index entities versus only public/helper-level contracts?
