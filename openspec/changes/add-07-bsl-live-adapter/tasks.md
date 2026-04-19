## 1. BSL live adapter
- [x] 1.1 Implement BSL repository detection and description through the adapter SPI.
- [x] 1.2 Register a minimal BSL-specific helper set for live analysis.
- [ ] 1.3 Support useful BSL exploration workflows without requiring a prebuilt index.

## 2. Acceptance
- [x] 2.1 Add tests for BSL repository detection.
- [ ] 2.2 Add tests for representative live-analysis helper flows on BSL fixtures.

Status note: Detection, adapter selection, repository description, and minimal helper registration are implemented. Remaining work for change closure is a richer live-analysis helper flow and acceptance coverage that proves representative BSL exploration before any prebuilt index exists.
