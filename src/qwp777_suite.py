"""CLI entry point for the built-in QWP-777 conformance suite."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from qwp777_conformance_suite import run_conformance_suite
from qwp777_experiment import ExperimentError
from qwp777_stabilizer import StabilizerError
from qwp777_validation import CircuitSchemaError
from qwp777_noise import NoiseModelError

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run built-in QWP-777 golden-circuit conformance checks.")
    parser.add_argument("--shots", type=int, default=512, help="shots per case (64..100000)")
    parser.add_argument("--seed", type=int, default=1777, help="base random seed")
    parser.add_argument("-o", "--output", help="write full conformance report JSON to this path")
    args = parser.parse_args(argv)
    try:
        report = run_conformance_suite(args.shots, args.seed)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0 if report["summary"]["passed"] else 1
    except (OSError, ValueError, ExperimentError, StabilizerError, CircuitSchemaError, NoiseModelError) as exc:
        print(f"qwp777-suite: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
