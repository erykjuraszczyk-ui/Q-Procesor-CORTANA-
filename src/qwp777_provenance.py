"""Create and verify a lightweight build-provenance statement for QWP-777.

Provenance is descriptive evidence. The release manifest signature is the
cryptographic binding over the included files; this report is not an attestation
from a third-party build service and does not prove the build was reproducible.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from qwp777_version import __version__, API_VERSION, RESULT_SCHEMA_VERSION

PROVENANCE_SCHEMA = "qwp777-build-provenance-1"
class ProvenanceError(ValueError):
    pass

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _relative_existing(root: Path, value: str) -> tuple[str, Path]:
    p = Path(value)
    if p.is_absolute():
        raise ProvenanceError(f"provenance input paths must be relative: {value}")
    posix = PurePosixPath(value)
    if not value or ".." in posix.parts or "\\" in value:
        raise ProvenanceError(f"unsafe provenance input path: {value}")
    candidate = root / p
    cursor = root
    for part in posix.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ProvenanceError(f"symbolic links are not allowed in provenance paths: {value}")
    target = candidate.resolve()
    try:
        rel = target.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ProvenanceError(f"provenance input escapes release root: {value}") from exc
    if not target.is_file() or target.is_symlink():
        raise ProvenanceError(f"provenance input is missing or is not a regular file: {value}")
    return rel, target

def create_provenance(root, output="docs/PROVENANCE.json", audit_report="docs/RELEASE_AUDIT.json",
                      test_report="docs/TEST_REPORT.json", source_release="2.8.0", source_archive=None):
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ProvenanceError(f"release root is not a directory: {root_path}")
    version = (root_path / "VERSION").read_text(encoding="utf-8").strip()
    if version != __version__:
        raise ProvenanceError(f"VERSION ({version}) does not match running provenance tool ({__version__})")
    inputs = {}
    required_inputs = (("release_audit", audit_report), ("test_report", test_report),
                       ("api_contract", f"compatibility/api-v{version}.json"),
                       ("regression_baseline", f"regression/baselines/v{version}.json"))
    optional_release_inputs = (("sbom", "docs/SBOM.cdx.json"),
                               ("dependency_audit", "docs/DEPENDENCY_AUDIT.json"))
    for label, value in required_inputs + tuple(
            (label, value) for label, value in optional_release_inputs
            if (root_path / value).is_file()):
        rel, path = _relative_existing(root_path, value)
        inputs[label] = {"path": rel, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
    prior = {"release": source_release or None, "archive": None}
    if source_archive:
        src = Path(source_archive).resolve()
        if not src.is_file():
            raise ProvenanceError(f"source release archive does not exist: {src}")
        prior["archive"] = {"name": src.name, "size_bytes": src.stat().st_size, "sha256": _sha256(src)}
    audit = json.loads((root_path / inputs["release_audit"]["path"]).read_text(encoding="utf-8"))
    try:
        test_report_obj = json.loads((root_path / inputs["test_report"]["path"]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        test_report_obj = {}
    report = {
        "provenance_schema": PROVENANCE_SCHEMA,
        "software": {"name": "QWP-777", "release": version, "api_version": API_VERSION,
                     "result_schema": RESULT_SCHEMA_VERSION},
        "derived_from": prior,
        "inputs": inputs,
        "validation": {
            "audit_passed": audit.get("summary", {}).get("passed") is True,
            "audit_checks_passed": audit.get("summary", {}).get("checks_passed"),
            "audit_checks_total": audit.get("summary", {}).get("checks_total"),
            "unit_tests_run": audit.get("unit_tests", {}).get("tests_run"),
            "test_report_schema": test_report_obj.get("report_schema", "not_recorded")
        },
        "build_environment": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "python_version": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "builder": "qwp777-provenance-tool",
            "builder_version": version,
            "repository_commit": None,
            "repository_commit_note": "Not recorded because this source directory does not provide a verified Git commit ID."
        },
        "caveats": [
            "This is a build-provenance summary, not an independently issued attestation.",
            "The embedded manifest and its detached Ed25519 signature bind the exact files; the ZIP SHA-256 sidecar binds the outer archive bytes.",
            "The source archive digest identifies the input archive but does not prove that this build was reproducible.",
            "Publisher identity requires independently trusting the public-key fingerprint."
        ]
    }
    out = Path(output)
    if out.is_absolute():
        try:
            out.relative_to(root_path)
        except ValueError as exc:
            raise ProvenanceError("provenance output must be inside the release root") from exc
    else:
        out = root_path / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report

def verify_provenance(root, provenance_path="docs/PROVENANCE.json", source_archive=None):
    root_path = Path(root).resolve()
    rel, path = _relative_existing(root_path, provenance_path)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProvenanceError(f"invalid provenance JSON: {exc}") from exc
    if report.get("provenance_schema") != PROVENANCE_SCHEMA:
        raise ProvenanceError("unsupported provenance schema")
    if report.get("software", {}).get("release") != (root_path / "VERSION").read_text(encoding="utf-8").strip():
        raise ProvenanceError("provenance version does not match VERSION")
    failures = []
    checked = 0
    inputs = report.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        raise ProvenanceError("provenance inputs must be a non-empty object")
    for label, record in inputs.items():
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            failures.append({"input": label, "reason": "malformed input record"})
            continue
        try:
            input_rel, input_path = _relative_existing(root_path, record["path"])
        except ProvenanceError as exc:
            failures.append({"input": label, "reason": str(exc)})
            continue
        checked += 1
        if record.get("sha256") != _sha256(input_path) or record.get("size_bytes") != input_path.stat().st_size:
            failures.append({"input": label, "path": input_rel, "reason": "size or SHA-256 mismatch"})
    source = report.get("derived_from", {}).get("archive")
    if source_archive and source:
        src = Path(source_archive)
        if not src.is_file():
            failures.append({"input": "source_archive", "reason": "source archive not found"})
        elif src.name != source.get("name") or src.stat().st_size != source.get("size_bytes") or _sha256(src) != source.get("sha256"):
            failures.append({"input": "source_archive", "reason": "size or SHA-256 mismatch"})
        else:
            checked += 1
    return {"report_schema": "qwp777-provenance-verification-1", "verified": not failures,
            "provenance_path": rel, "inputs_checked": checked, "failures": failures,
            "source_archive_checked": bool(source_archive and source)}

def main(argv=None):
    parser = argparse.ArgumentParser(description="Create or verify QWP-777 build provenance.")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--root", default=".")
    create.add_argument("--output", default="docs/PROVENANCE.json")
    create.add_argument("--audit-report", default="docs/RELEASE_AUDIT.json")
    create.add_argument("--test-report", default="docs/TEST_REPORT.json")
    create.add_argument("--source-release", default="2.8.0")
    create.add_argument("--source-archive")
    verify = sub.add_parser("verify")
    verify.add_argument("--root", default=".")
    verify.add_argument("--provenance", default="docs/PROVENANCE.json")
    verify.add_argument("--source-archive")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create_provenance(args.root, args.output, args.audit_report, args.test_report,
                                       args.source_release, args.source_archive)
        else:
            result = verify_provenance(args.root, args.provenance, args.source_archive)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "verify":
            return 0 if result["verified"] else 1
        return 0
    except (OSError, ProvenanceError, json.JSONDecodeError) as exc:
        print(f"qwp777-provenance: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
