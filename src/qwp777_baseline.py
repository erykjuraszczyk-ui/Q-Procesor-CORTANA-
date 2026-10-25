"""Explicit, versioned baseline refresh workflow for fixed-seed regressions."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from qwp777_experiment import run_experiment
from qwp777_version import __version__

class BaselineRefreshError(ValueError):
    pass

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")

def refresh_baseline(source_path, output_path, baseline_version, approved=False):
    if not approved:
        raise BaselineRefreshError("baseline refresh requires explicit approval (--approve)")
    if not isinstance(baseline_version, str) or not _VERSION_RE.fullmatch(baseline_version):
        raise BaselineRefreshError("baseline_version must be a semantic version such as 1.7.0")
    source = Path(source_path)
    output = Path(output_path)
    if output.exists() or Path(str(output)+".sha256").exists():
        raise BaselineRefreshError("refusing to overwrite an existing baseline or checksum")
    try:
        original_bytes = source.read_bytes()
        fixture = json.loads(original_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineRefreshError(f"cannot read source baseline: {exc}") from exc
    if not isinstance(fixture, dict) or fixture.get("baseline_schema") != "qwp777-regression-baseline-1":
        raise BaselineRefreshError("source baseline has an unsupported schema")
    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        raise BaselineRefreshError("source baseline must contain at least one case")
    new_cases = []
    names = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise BaselineRefreshError(f"source case {index} must be an object")
        name = case.get("name")
        if not isinstance(name, str) or not name or name in names:
            raise BaselineRefreshError(f"source case {index} has an invalid/duplicate name")
        names.add(name)
        try:
            result = run_experiment(case["num_qubits"], case["gates"],
                                    case["shots"], case["seed"],
                                    case.get("noise_probability", 0.0))
        except (KeyError, TypeError, ValueError) as exc:
            raise BaselineRefreshError(f"cannot reproduce case {name}: {exc}") from exc
        new_cases.append({
            "name": name,
            "num_qubits": case["num_qubits"],
            "gates": case["gates"],
            "shots": case["shots"],
            "seed": case["seed"],
            "noise_probability": case.get("noise_probability", 0.0),
            "expected_counts": result["counts"]
        })
    project_root = Path(__file__).resolve().parents[1]
    try:
        source_record = str(source.resolve().relative_to(project_root))
    except ValueError:
        source_record = source.name
    payload = {
        "baseline_schema": "qwp777-regression-baseline-1",
        "baseline_release": baseline_version,
        "captured_by_release": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parent_baseline": {
            "path": source_record,
            "sha256": hashlib.sha256(original_bytes).hexdigest(),
            "baseline_release": fixture.get("baseline_release")
        },
        "refresh_policy": "explicitly-approved; original baseline preserved",
        "cases": new_cases
    }
    encoded = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids overwriting a baseline created concurrently.
    try:
        with output.open("xb") as stream:
            stream.write(encoded)
        with Path(str(output)+".sha256").open("x", encoding="utf-8") as stream:
            stream.write(f"{hashlib.sha256(encoded).hexdigest()}  {output.name}\n")
    except FileExistsError as exc:
        raise BaselineRefreshError("baseline or checksum appeared during refresh; no overwrite was performed") from exc
    return {
        "report_schema": "qwp777-baseline-refresh-report-1",
        "approved": True,
        "baseline_version": baseline_version,
        "output": str(output),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "source_sha256": payload["parent_baseline"]["sha256"],
        "cases_written": len(new_cases),
        "notes": ["The source baseline was read-only and was not modified.",
                  "Review the generated counts and checksum before treating the refreshed baseline as a trusted release artifact."]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Refresh regression counts into a new, versioned baseline without overwriting the old one.")
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1] / "regression" / "baselines" / "v1.5.0.json"))
    parser.add_argument("--output", help="output JSON; default is regression/baselines/<baseline-version>.json")
    parser.add_argument("--baseline-version", required=True, help="version label for the new baseline, e.g. 1.7.0")
    parser.add_argument("--approve", action="store_true", help="explicitly approve generating a new baseline")
    parser.add_argument("--report", help="write operation summary JSON to this path")
    args = parser.parse_args(argv)
    try:
        output = args.output or str(Path(__file__).resolve().parents[1] / "regression" / "baselines" / f"v{args.baseline_version}.json")
        result = refresh_baseline(args.source, output, args.baseline_version, args.approve)
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.report:
            Path(args.report).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, BaselineRefreshError) as exc:
        print(f"qwp777-baseline: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
