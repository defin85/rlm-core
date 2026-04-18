# Change: Add Go second adapter

## Why
The architecture should not be considered proven until at least one non-BSL adapter validates the shared contracts. Go is a strong second-adapter candidate because it has a mature semantic tooling ecosystem and materially different workspace behavior from BSL.

## What Changes
- Add a Go adapter as the second real adapter in the system.
- Validate generic runtime, lifecycle, and index abstractions against Go repository workflows.
- Use Go-specific tooling only through adapter-owned boundaries.

## Impact
- Affected specs: `go-second-adapter`
- Affected code: future Go adapter package, Go adapter tests, capability negotiation coverage
