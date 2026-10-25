"""Check backward compatibility against a saved public API contract."""
from __future__ import annotations
import argparse, importlib, inspect, json, sys
from pathlib import Path
from qwp777_version import __version__, API_VERSION, RESULT_SCHEMA_VERSION

class ApiCompatibilityError(ValueError):
    pass

_DEFAULT_CONTRACT = Path(__file__).resolve().parents[1] / "compatibility" / "api-v1.6.0.json"

def check_api_compatibility(contract_path=None):
    path = Path(contract_path) if contract_path else _DEFAULT_CONTRACT
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApiCompatibilityError(f"cannot load API contract: {exc}") from exc
    if contract.get("compatibility_schema") != "qwp777-api-compatibility-1":
        raise ApiCompatibilityError("unsupported compatibility contract schema")
    try:
        api = importlib.import_module("qwp777_api")
    except ImportError as exc:
        raise ApiCompatibilityError(f"cannot import qwp777_api: {exc}") from exc
    expected_exports = contract.get("public_exports", [])
    if not isinstance(expected_exports, list) or not expected_exports:
        raise ApiCompatibilityError("contract public_exports must be a non-empty list")
    current_exports = set(getattr(api, "__all__", []))
    missing = sorted(set(expected_exports) - current_exports)
    required_callable = contract.get("required_callable_exports", [])
    not_callable = sorted(name for name in required_callable if not callable(getattr(api, name, None)))
    expected_signatures = contract.get("callable_signatures", {})
    signature_diffs = {}
    for name, expected in expected_signatures.items():
        obj = getattr(api, name, None)
        if not callable(obj):
            signature_diffs[name] = {"expected": expected, "actual": None}
            continue
        try:
            actual = str(inspect.signature(obj))
        except (TypeError, ValueError):
            actual = None
        if actual != expected:
            signature_diffs[name] = {"expected": expected, "actual": actual}
    schema_ok = RESULT_SCHEMA_VERSION == contract.get("experiment_result_schema")
    report = {
        "report_schema": "qwp777-api-compatibility-report-1",
        "current": {"release": __version__, "api_version": API_VERSION,
                    "experiment_result_schema": RESULT_SCHEMA_VERSION},
        "contract": {"path": str(path), "snapshot_release": contract.get("snapshot_release"),
                     "snapshot_api_version": contract.get("snapshot_api_version")},
        "checks": {
            "legacy_exports_present": not missing,
            "required_symbols_callable": not not_callable,
            "callable_signatures_unchanged": not signature_diffs,
            "result_schema_unchanged": schema_ok
        },
        "missing_exports": missing,
        "non_callable_required_exports": not_callable,
        "signature_differences": signature_diffs,
        "compatible": not (missing or not_callable or signature_diffs or not schema_ok),
        "notes": [
            "Source-level compatibility checks do not prove semantic behavior compatibility.",
            "Use immutable, versioned contract snapshots; the release audit independently checks the v1.6.0 legacy gate and the explicitly selected current-release contract."
        ]
    }
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the current public API against a saved compatibility contract.")
    parser.add_argument("--contract", help="contract JSON path; defaults to the bundled v1.6.0 contract")
    parser.add_argument("-o", "--output", help="write report JSON to path")
    args = parser.parse_args(argv)
    try:
        report = check_api_compatibility(args.contract)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0 if report["compatible"] else 1
    except (OSError, ApiCompatibilityError) as exc:
        print(f"qwp777-api-compat: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
