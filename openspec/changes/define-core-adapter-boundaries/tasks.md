## 1. Core architecture
- [ ] 1.1 Define `WorkspaceRegistry` / `ProjectRegistry` abstractions in `rlm_core` with support for both registered workspaces and direct path execution.
- [ ] 1.2 Define `IndexManager` in `rlm_core` for `build`, `update`, `drop`, `info`, `check`, locking, status reporting, and background job orchestration.
- [ ] 1.3 Define adapter capabilities and index lifecycle contracts used by the core orchestration layer.

## 2. Adapter boundary
- [ ] 2.1 Define the adapter contract for `detect`, `describe_repo`, index build/read hooks, helper registration, and strategy/context hooks.
- [ ] 2.2 Move BSL-specific index implementation and metadata/schema extensions behind the adapter contract without moving them into `core`.
- [ ] 2.3 Preserve a uniform external API for `rlm_start`, `rlm_execute`, `rlm_end`, `rlm_projects`, and `rlm_index` while routing behavior through core-owned lifecycle services.

## 3. Validation
- [ ] 3.1 Add tests for path-only operation without registry entries.
- [ ] 3.2 Add tests for registry-backed operation and authorization/confirmation policy on mutating actions.
- [ ] 3.3 Add tests covering adapters with and without prebuilt index support so capability negotiation is exercised explicitly.
