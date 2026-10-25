# Migration guide: QWP-777 v1.x → v2.0.0

## What changed

- Software release: `1.9.0` → `2.0.0`.
- Public API version: `1.9` → `2.0`.
- Experiment result schema: unchanged at `qwp777-experiment-1`.
- Public export names and callable signatures are preserved by the v2 contract snapshot.
- Release audit now checks both the frozen v1.6.0 legacy contract and the new v2.0.0 contract, plus historical and current regression baselines.

## Consumer actions

1. Update any strict version allow-list that only accepts API `1.9` to accept API `2.0`.
2. Keep parsing experiment results according to `qwp777-experiment-1`; no result-schema migration is required for this release.
3. Run your integration tests and review `compatibility/api-v2.0.0.json` before deploying.
4. If your own code checks `release`, expect `2.0.0`.

## Python usage

The basic call remains unchanged:

```python
import sys
sys.path.insert(0, "src")
from qwp777_api import run_circuit

result = run_circuit({
    "num_qubits": 1,
    "gates": [{"gate": "X", "qubits": [0]}, {"gate": "MEASURE", "qubits": [0]}],
    "shots": 100,
    "seed": 7,
})
print(result["release"])       # 2.0.0
print(result["api_version"])   # 2.0
print(result["schema_version"])  # qwp777-experiment-1
```

## Compatibility notes

This is a major API-contract generation, not a claim that every symbol was removed or redesigned. In this release, signatures are intentionally retained to make migration low-risk. The API contract is source-level evidence; application-level behavior still needs testing in the consumer's environment.
