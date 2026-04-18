## 1. Core architecture
- [x] 1.1 Define `WorkspaceRegistry` / `ProjectRegistry` abstractions in `rlm_core` with support for both registered workspaces and direct path execution.
- [x] 1.2 Define `IndexManager` in `rlm_core` for `build`, `update`, `drop`, `info`, `check`, locking, status reporting, and background job orchestration.
- [x] 1.3 Define adapter capabilities and index lifecycle contracts used by the core orchestration layer.

## 2. Adapter boundary
- [x] 2.1 Define the adapter contract for `detect`, `describe_repo`, index build/read hooks, helper registration, and strategy/context hooks.
- [x] 2.2 Move BSL-specific index implementation and metadata/schema extensions behind the adapter contract without moving them into `core`.
- [x] 2.3 Preserve a uniform external API for `rlm_start`, `rlm_execute`, `rlm_end`, `rlm_projects`, and `rlm_index` while routing behavior through core-owned lifecycle services.

## 3. Validation
- [x] 3.1 Add tests for path-only operation without registry entries.
- [x] 3.2 Add tests for registry-backed operation and authorization/confirmation policy on mutating actions.
- [x] 3.3 Add tests covering adapters with and without prebuilt index support so capability negotiation is exercised explicitly.
