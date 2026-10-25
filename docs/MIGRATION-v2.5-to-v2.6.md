# Migration notes: QWP-777 v2.5.0 → v2.6.0

## Compatibility

- Public exports and callable signatures in `qwp777_api` remain unchanged.
- Experiment result schema remains `qwp777-experiment-1`.
- API version metadata advances from `2.5` to `2.6`; release metadata advances from `2.5.0` to `2.6.0`.
- The v2.5.0 API snapshot and regression baseline are preserved. The new snapshots are `compatibility/api-v2.6.0.json` and `regression/baselines/v2.6.0.json`.

## New CLI tool

`src/qwp777_release_series.py` accepts paths to JSON release audit, regression, and consolidated health reports. It emits a history report in JSON and HTML. The tool does not re-run tests and does not infer success from missing information.

Example:

```bash
python src/qwp777_release_series.py \
  compatibility/reports/v2.4.0-regression.json \
  compatibility/reports/v2.5.0-regression.json \
  compatibility/reports/v2.6.0-regression.json \
  docs/RELEASE_AUDIT.json \
  --json release-series.json --html release-series.html
```

## Status semantics

- `failed`: a provided audit/regression report failed, or a test that previously passed now fails.
- `review_required`: the supplied health report requests review or adjacent regression reports show distribution/case-set changes.
- `history_clean_or_informational`: no failure/review trigger was found in supplied inputs; it is not a correctness proof.

No source-level API migration is needed for existing `qwp777_api` consumers. Review generated reports before using them as release sign-off evidence.
