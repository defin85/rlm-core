## 1. BSL indexed acceleration
- [x] 1.1 Implement BSL index build and read hooks behind the adapter SPI.
- [x] 1.2 Connect BSL indexed workflows to the shared index lifecycle service.
- [ ] 1.3 Accelerate the highest-value BSL discovery and call/navigation workflows through indexed reads.

## 2. Acceptance
- [ ] 2.1 Add tests for BSL build, info, and update-or-rebuild lifecycle flows.
- [ ] 2.2 Add tests proving indexed helpers behave correctly when the BSL index is present.

Status note: Adapter-owned manifest lifecycle hooks and core lifecycle routing are implemented. Remaining work for change closure is indexed helper acceleration plus acceptance coverage for update-or-rebuild and indexed helper behavior.
