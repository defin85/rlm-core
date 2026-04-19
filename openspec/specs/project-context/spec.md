# project-context Specification

## Purpose
TBD - created by archiving change document-project-context. Update Purpose after archive.
## Requirements
### Requirement: OpenSpec project context must be populated
The repository SHALL maintain `openspec/project.md` as a populated project-context document rather than leaving it as the default template.

#### Scenario: Initialize project context from repository sources of truth
- **WHEN** the repository has enough established context in its README, architecture notes, package metadata, and repo instructions
- **THEN** `openspec/project.md` contains concrete purpose, stack, conventions, domain context, constraints, and dependency guidance
- **AND** placeholder template prompts are removed

### Requirement: Future changes must be grounded in project context
The repository SHALL treat `openspec/project.md` as a required context source for future OpenSpec changes that affect architecture, capabilities, or implementation conventions.

#### Scenario: Author a future OpenSpec change
- **WHEN** an author creates or updates a future OpenSpec change
- **THEN** the author can rely on `openspec/project.md` for project-specific guidance instead of generic template assumptions
- **AND** project context stays aligned with the repository's intended architecture direction

