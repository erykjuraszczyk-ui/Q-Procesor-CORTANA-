# Migration: QWP-777 v2.3.0 → v2.4.0

## API

The public export list, callable signatures and `qwp777-experiment-1` result schema are unchanged. Release metadata reports API 2.4; old contract snapshots are preserved.

## Diagnostics

Analyze a soak report:

```bash
python src/qwp777_stability_analyze.py soak-report.json -o stability-analysis.json
```

Compare runs from two hosts only when the workload parameters match:

```bash
python src/qwp777_device_compare.py phone-soak.json linux-soak.json -o device-comparison.json
```

Anomaly findings are conservative heuristics, not proof of a leak. RSS can be unavailable and `tracemalloc` is not total process RAM. Cross-device timing differences are descriptive, not causal proof.
