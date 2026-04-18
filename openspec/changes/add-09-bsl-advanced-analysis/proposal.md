# Change: Add BSL advanced analysis

## Why
After live analysis and the core BSL prebuilt index are in place, the remaining BSL-specific differentiators should be migrated explicitly as adapter-owned extensions rather than folded into the shared core.

## What Changes
- Add advanced BSL analysis capabilities such as metadata enrichments and specialized indexed helper flows.
- Keep these capabilities in adapter-owned extension layers.
- Extend BSL helper coverage without reshaping the shared core around BSL details.

## Impact
- Affected specs: `bsl-advanced-analysis`
- Affected code: future BSL extension features, adapter-owned metadata enrichments, advanced BSL helper coverage
