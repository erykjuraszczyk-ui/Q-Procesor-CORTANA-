"""Compare two result JSON files and emit a complete statistical report."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
from qwp777_conformance import compare_result_payloads, ConformanceError
from qwp777_confidence import compare_proportion_intervals, ConfidenceError
from qwp777_significance import chi_square_two_sample_test, SignificanceError
from qwp777_version import __version__, API_VERSION

def _input_summary(result):
    return {
        "release": result.get("release"),
        "api_version": result.get("api_version"),
        "backend": result.get("backend"),
        "num_qubits": result.get("num_qubits"),
        "shots": result.get("shots", sum(result.get("counts", {}).values())),
        "measured_qubits": result.get("measured_qubits"),
        "noise_model": result.get("noise_model")
    }

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare two result JSON files and emit a complete statistical report.")
    parser.add_argument("left", help="first result JSON")
    parser.add_argument("right", help="second result JSON")
    parser.add_argument("--confidence-level", type=float, default=0.95,
                        choices=[0.80, 0.90, 0.95, 0.98, 0.99],
                        help="confidence level for outcome-wise intervals (default: 0.95)")
    parser.add_argument("--alpha", type=float, default=0.05,
                        choices=[0.01, 0.05, 0.10],
                        help="significance threshold for the chi-square test (default: 0.05)")
    parser.add_argument("-o", "--output", help="write the complete report JSON to this path")
    args = parser.parse_args(argv)
    try:
        left = json.loads(Path(args.left).read_text(encoding="utf-8"))
        right = json.loads(Path(args.right).read_text(encoding="utf-8"))
        comparison = compare_result_payloads(left, right)
        confidence = compare_proportion_intervals(left["counts"], right["counts"], args.confidence_level)
        significance = chi_square_two_sample_test(left["counts"], right["counts"], args.alpha)
        if significance["status"] == "difference_detected":
            assessment = "distribution_difference_detected"
        elif significance["status"] == "no_significant_difference_detected":
            assessment = "no_significant_difference_detected"
        else:
            assessment = "inconclusive"
        report = {
            "report_schema": "qwp777-experiment-report-1",
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "software": {"release": __version__, "api_version": API_VERSION},
            "input_summary": {"left": _input_summary(left), "right": _input_summary(right)},
            **comparison,
            "confidence_analysis": confidence,
            "significance_analysis": significance,
            "assessment": assessment,
            "caveats": [
                "Statistical analysis assumes the two samples come from equivalent circuit/measurement configurations.",
                "A non-significant result is not proof of equivalence.",
                "The chi-square test is asymptotic and is withheld when any expected cell count is below 5.",
                "The p-value is not adjusted for multiple comparisons.",
                "This report does not prove either backend is correct or reproduce physical-device behavior."
            ]
        }
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, ConformanceError, ConfidenceError, SignificanceError, TypeError, KeyError) as exc:
        print(f"qwp777-compare: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
