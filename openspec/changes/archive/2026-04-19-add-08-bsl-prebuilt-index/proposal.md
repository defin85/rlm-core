# Change: Add BSL prebuilt index

## Why
Live analysis proves the adapter shape, but BSL repositories can be large enough that indexed acceleration becomes operationally important. The next step is to migrate the BSL prebuilt index behind the shared core lifecycle.

## What Changes
- Add BSL index builder and reader implementations behind the adapter SPI.
- Support BSL prebuilt index lifecycle through the core-owned lifecycle service.
- Accelerate the highest-value BSL workflows with indexed reads.

## Impact
- Affected specs: `bsl-prebuilt-index`
- Affected code: future BSL index builder/reader, BSL lifecycle hooks, indexed helper integration
