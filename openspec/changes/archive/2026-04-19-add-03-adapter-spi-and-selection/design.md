## Context

The runtime should know how to load and select adapters, but it should not know language-specific parsing or indexing details.

## Decisions

- Adapters are selected after workspace resolution.
- Capabilities are explicit rather than inferred from optional methods.
- The SPI includes helper registration and index-related hooks, but not public API ownership.

## Risks / Trade-offs

- An SPI that is too broad will freeze bad abstractions early.
  - Mitigation: keep the initial contract narrow and validate it with stubs before deep adapter migrations.
