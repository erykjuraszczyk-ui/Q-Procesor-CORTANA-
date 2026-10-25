# API versioning policy

Every release checks the immutable v1.6.0 legacy contract and the current release contract. `compatibility/api-v2.3.0.json` freezes v2.3 public export names and callable signatures.

For v2.3.0, the API version is `2.3`; the experiment result schema remains `qwp777-experiment-1`. Soak testing and profile comparison are opt-in command-line diagnostics and do not expand `qwp777_api.__all__`. A breaking change to exported names, function signatures or result schema requires a documented migration and contract transition.

Older API snapshots and regression baselines are historical evidence and must not be rewritten to current values.


## v2.4.0 note

API 2.4 preserves the frozen v2.3 public export surface and `qwp777-experiment-1` result schema. The release adds opt-in diagnostic scripts only; historical API snapshots remain immutable.


## v2.5.0
The API version metadata advances to 2.5. The experiment result schema remains `qwp777-experiment-1`; the health report is an optional diagnostic utility and does not change result payloads.
