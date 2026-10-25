# Migration guide: QWP-777 v2.0.0 → v2.1.0

- Software release: `2.0.0` → `2.1.0`.
- API version: `2.0` → `2.1`.
- Public function names/signatures and experiment result schema `qwp777-experiment-1` are unchanged.
- Update API version checks from `2.0` to `2.1` if your client explicitly pins the release API version.
- Optional diagnostic commands are `python src/qwp777_profile.py CIRCUIT.json --repeats 5` and `python src/qwp777_runtime_info.py`.
- Profiler memory numbers represent traced Python allocations, not system-wide or full process RSS. Performance depends on the device and workload.
- Historical API snapshots and regression baselines are preserved.
