# QWP-777 v1.0.0 Stable — Release Checklist

## Local package verification
- [x] Set release metadata to `1.0.0`.
- [x] Keep API version `1.0` and result schema `qwp777-experiment-1`.
- [x] Run the unit-test suite during packaging.
- [x] Run the bundled CLI examples and parse their JSON output.
- [x] Verify the archive structure and SHA-256 after packaging.
- [ ] Optional maintainer follow-up: test on the specific target Termux/Linux/Windows environments.
- [ ] Optional maintainer follow-up: compare circuits against a mature independent simulator.

## Scope
The checked items describe local build and package checks only. They do not imply physical-hardware testing, formal verification, or independent scientific validation.
