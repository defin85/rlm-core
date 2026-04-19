## 1. Shared authority contracts
- [ ] 1.1 Define shared authority, provenance, and claim-status vocabulary for analysis workflows.
- [ ] 1.2 Extend the adapter SPI with optional adapter-owned analysis provider contracts and backend declarations.
- [ ] 1.3 Define how helpers and sessions advertise authority information without relying on adapter-specific conventions.

## 2. Runtime and public surface
- [ ] 2.1 Surface machine-readable authority and backend metadata in session start and related public/runtime contracts.
- [ ] 2.2 Normalize how analysis helpers distinguish possible versus resolved relationships.
- [ ] 2.3 Make heuristic-only fallback behavior explicit when no semantic or authoritative backend is available.

## 3. Quality gates and documentation
- [ ] 3.1 Add authority-aware correctness evals that guard against overclaiming.
- [ ] 3.2 Add cross-adapter contract tests for authority signaling and provenance semantics.
- [ ] 3.3 Update architecture and public documentation to explain the trust model and adapter responsibilities.

## 4. Validation
- [ ] 4.1 Validate the new OpenSpec change with `openspec validate add-14-analysis-authority-model --strict --no-interactive`.
