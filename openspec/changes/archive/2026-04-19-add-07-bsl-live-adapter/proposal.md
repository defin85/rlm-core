# Change: Add BSL live adapter

## Why
The first real adapter should prove that the new runtime and adapter SPI can support meaningful language-specific analysis even before prebuilt indexing is migrated. BSL is the natural first adapter because `rlm-tools-bsl` is the primary migration source.

## What Changes
- Add a BSL adapter that supports repository detection and live filesystem-based analysis.
- Register a minimal but useful BSL-specific helper set through the adapter SPI.
- Support useful BSL exploration before prebuilt index migration.

## Impact
- Affected specs: `bsl-live-adapter`
- Affected code: future BSL adapter package, BSL live helper registration, BSL adapter tests
