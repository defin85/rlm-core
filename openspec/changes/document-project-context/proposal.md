# Change: Document project context for OpenSpec

## Why
`openspec/project.md` is still the default template, which means future change proposals do not have an authoritative project context to rely on. This increases the chance of generic or BSL-shaped assumptions leaking into later architecture and implementation work.

## What Changes
- Replace the placeholder content in `openspec/project.md` with the current purpose, stack, conventions, architecture direction, and constraints of `rlm-core`.
- Capture the current relationship to `rlm-tools` and `rlm-tools-bsl` so future OpenSpec changes start from the intended migration baseline.
- Record current workflow expectations around OpenSpec, Beads, verification, and direct-path versus registry-backed operation.
- Introduce an OpenSpec governance capability for maintaining project context as a first-class artifact.

## Impact
- Affected specs: `project-context`
- Affected docs: `openspec/project.md`
