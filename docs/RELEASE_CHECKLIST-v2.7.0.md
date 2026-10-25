# Release checklist — v2.7.0

- [ ] Run unit tests and the unified release audit.
- [ ] Verify the current API snapshot and historical snapshots.
- [ ] Verify the fixed-seed regression baseline and its checksum.
- [ ] Generate and review the release-series report.
- [ ] Build the release manifest after all reports are finalized.
- [ ] Verify all manifest file paths, byte lengths, and SHA-256 digests.
- [ ] Build ZIP outside the release root.
- [ ] Run ZIP CRC validation and verify the detached SHA-256 sidecar.
- [ ] If publisher identity matters, sign the release archive using a trusted key; SHA-256 alone is not a signature.
- [ ] Perform a separate run on target Android/Termux hardware before claiming Android validation.
