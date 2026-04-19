## Context

The repository should not rely on intuition alone for its core claims about safety, latency, and context efficiency.

## Decisions

- Quality gates are added only after a real public surface exists.
- Benchmarks and evals should use repeatable fixtures where possible.
- Safety checks must cover sandbox persistence, timeouts, and lifecycle edge cases.

## Risks / Trade-offs

- Evaluation infrastructure can expand quickly.
  - Mitigation: start with the highest-signal scenarios that exercise the core value proposition.
