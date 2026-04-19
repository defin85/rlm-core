# Change: Add workspace registry

## Why
The architecture decision already states that registry-backed operation is core-owned and optional. After path-only lifecycle exists, the next step is to add a consistent workspace/project registry so named workspaces can use the same runtime and lifecycle flows.

## What Changes
- Introduce the core-owned workspace/project registry abstraction.
- Support named workspace resolution for runtime and lifecycle operations.
- Add confirmation or authorization policy for mutating registry actions.

## Impact
- Affected specs: `workspace-registry`
- Affected code: future registry service, workspace resolution, mutation policy, registry tests
