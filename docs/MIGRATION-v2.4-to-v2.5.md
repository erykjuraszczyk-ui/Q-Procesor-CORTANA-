# Migration: v2.4.0 → v2.5.0

- Python runtime: use the same invocation pattern as v2.4.0.
- API version metadata is now `2.5`; the experiment result schema remains `qwp777-experiment-1`.
- New optional tool `src/qwp777_health_report.py` aggregates existing JSON reports into JSON and HTML. It does not rerun tests or upgrade informational statuses to passed.
- Existing diagnostic tools remain available.
