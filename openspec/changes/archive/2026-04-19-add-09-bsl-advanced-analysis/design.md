## Context

`rlm-tools-bsl` contains many advanced BSL features beyond the minimal adapter and prebuilt index. These features are valuable, but they are precisely the kind of language-specific detail that can easily pollute the shared core if migrated carelessly.

## Decisions

- Advanced BSL capabilities are migrated only after the live and indexed BSL baselines exist.
- The shared core remains unaware of BSL-specific enrichment details.
- Adapter capability declarations are used to expose advanced functionality explicitly.

## Risks / Trade-offs

- This slice can become too large if every advanced BSL feature is bundled together.
  - Mitigation: split the change further if implementation scope expands beyond a manageable vertical slice.
