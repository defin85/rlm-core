# Change: Add public API surface

## Why
The external MCP and CLI surface should not be stabilized before the runtime, lifecycle, and first production adapter have proved the internal architecture. Once that baseline exists, the repository needs a coherent public product surface.

## What Changes
- Define the stable public MCP-facing tool surface over the shared runtime and lifecycle services.
- Add a coherent CLI surface for lifecycle and operational workflows.
- Keep public semantics uniform across adapters.

## Impact
- Affected specs: `public-api-surface`
- Affected code: future MCP routing, CLI entrypoints, public request/response contracts
