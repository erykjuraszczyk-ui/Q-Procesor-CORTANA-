"""Memory preflight estimates for the QWP-777 stabilizer tableau.

The estimate covers Python list containers used by the X/Z matrices and phase vector.
It is not a prediction of process RSS and excludes integer objects, simulator overhead,
measurement counts, imported modules, and allocator fragmentation.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

class MemoryEstimateError(ValueError):
    pass

def estimate_tableau_memory(num_qubits: int) -> dict:
    if isinstance(num_qubits, bool) or not isinstance(num_qubits, int) or not 1 <= num_qubits <= 777:
        raise MemoryEstimateError("num_qubits must be an integer in 1..777")
    n = num_qubits
    # Match the list dimensions created by StabilizerSimulator: X and Z each contain 2n rows.
    row_bytes = sys.getsizeof([0] * n)
    outer_bytes = sys.getsizeof([None] * (2 * n))
    phase_bytes = sys.getsizeof([0] * (2 * n))
    row_containers = 4 * n
    container_bytes = row_containers * row_bytes + 2 * outer_bytes + phase_bytes
    return {
        "num_qubits": n,
        "matrix_rows_total": row_containers,
        "matrix_slots_total": 4 * n * n,
        "estimated_list_container_bytes": container_bytes,
        "estimated_list_container_mib": container_bytes / (1024 * 1024),
        "estimator": "sys.getsizeof list-container estimate",
        "scope": "X/Z matrix row and outer lists plus phase vector; excludes element objects and total process RSS",
        "interpretation": "Host/Python-specific estimate, not a memory guarantee."
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Estimate QWP-777 stabilizer tableau list-container memory.")
    parser.add_argument("num_qubits", type=int, help="qubit count (1..777)")
    parser.add_argument("-o", "--output", help="write JSON report to this path")
    args = parser.parse_args(argv)
    try:
        report = {"report_schema": "qwp777-memory-estimate-1", **estimate_tableau_memory(args.num_qubits)}
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (MemoryEstimateError, OSError) as exc:
        print(f"qwp777-memory: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
