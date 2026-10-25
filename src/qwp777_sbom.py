"""Generate and verify a CycloneDX 1.6 SBOM for QWP-777.

The SBOM describes declared optional integrations. Their environment-observed
versions are recorded as properties and are not dependency pins or a lockfile.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SBOM_SCHEMA_VERSION = "1.6"
SBOM_SCHEMA = "qwp777-sbom-report-1"

class SbomError(ValueError):
    pass

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _read_policy(root: Path, policy_path: str | Path = "DEPENDENCIES.json") -> dict:
    path = Path(policy_path)
    if not path.is_absolute():
        path = root / path
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SbomError(f"cannot read dependency policy: {exc}") from exc
    if policy.get("dependency_policy_schema") != "qwp777-dependency-policy-1":
        raise SbomError("unsupported dependency policy schema")
    return policy

def _observed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None

def create_sbom(root: str | Path, output: str | Path = "docs/SBOM.cdx.json",
                policy_path: str | Path = "DEPENDENCIES.json") -> dict:
    root = Path(root).resolve()
    if not root.is_dir():
        raise SbomError(f"SBOM root is not a directory: {root}")
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    policy_path_abs = Path(policy_path)
    if not policy_path_abs.is_absolute():
        policy_path_abs = root / policy_path_abs
    policy = _read_policy(root, policy_path)
    app_ref = f"pkg:generic/QWP-777@{version}"
    components = []
    dependency_refs = []
    for item in policy.get("optional_dependencies", []):
        if not isinstance(item, dict) or not item.get("name") or not item.get("purl"):
            raise SbomError("malformed optional dependency policy entry")
        purl = item["purl"]
        observed = _observed_version(item["distribution"])
        props = [
            {"name": "qwp777:scope", "value": "optional"},
            {"name": "qwp777:feature", "value": str(item.get("feature", ""))},
            {"name": "qwp777:version-policy", "value": str(item.get("version_policy", "unlocked"))},
            {"name": "qwp777:observed-build-environment-version", "value": observed or "not-installed"},
        ]
        component = {
            "type": "library", "name": item["name"], "bom-ref": purl,
            "purl": purl, "scope": "optional", "properties": props
        }
        components.append(component)
        dependency_refs.append(purl)
    report = {
        "bomFormat": "CycloneDX",
        "specVersion": SBOM_SCHEMA_VERSION,
        "serialNumber": "urn:uuid:" + str(uuid.uuid4()),
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tools": {"components": [{
                "type": "application", "name": "qwp777-sbom-generator", "version": version,
                "purl": f"pkg:generic/qwp777-sbom-generator@{version}"
            }]},
            "component": {
                "type": "application", "name": "QWP-777", "version": version,
                "bom-ref": app_ref, "purl": app_ref,
                "description": "Programmatic stabilizer-circuit simulator prototype; not physical quantum hardware."
            },
            "properties": [
                {"name": "qwp777:report-schema", "value": SBOM_SCHEMA},
                {"name": "qwp777:dependency-policy-sha256", "value": sha256_file(policy_path_abs)},
                {"name": "qwp777:lockfile-present", "value": "false"},
                {"name": "qwp777:build-python", "value": sys.version.split()[0]},
                {"name": "qwp777:build-platform", "value": platform.platform()},
            ]
        },
        "components": components,
        "dependencies": [{"ref": app_ref, "dependsOn": dependency_refs}],
        "compositions": [{"aggregate": "incomplete", "assemblies": [app_ref],
                          "dependencies": [item["purl"] for item in components]}],
        "properties": [
            {"name": "qwp777:vulnerability-scan", "value": "not-performed-offline"},
            {"name": "qwp777:dependency-version-locking", "value": "not-configured"},
            {"name": "qwp777:component-inventory", "value": "declared-optional-integrations"}
        ]
    }
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path
    try:
        output_path.resolve().relative_to(root)
    except ValueError as exc:
        raise SbomError("SBOM output must be inside the release root") from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report

def verify_sbom(root: str | Path, sbom_path: str | Path = "docs/SBOM.cdx.json",
                policy_path: str | Path = "DEPENDENCIES.json") -> dict:
    root = Path(root).resolve()
    target = Path(sbom_path)
    if not target.is_absolute():
        target = root / target
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SbomError(f"cannot read SBOM: {exc}") from exc
    policy = _read_policy(root, policy_path)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    expected = {item["purl"] for item in policy.get("optional_dependencies", [])}
    seen = {item.get("purl") for item in data.get("components", []) if isinstance(item, dict)}
    missing, unexpected = sorted(expected - seen), sorted(seen - expected)
    app = data.get("metadata", {}).get("component", {})
    policy_hash = sha256_file(root / policy_path)
    metadata_props = {p.get("name"): p.get("value") for p in data.get("metadata", {}).get("properties", [])}
    checks = {
        "cyclonedx_format": data.get("bomFormat") == "CycloneDX",
        "cyclonedx_version": data.get("specVersion") == SBOM_SCHEMA_VERSION,
        "application_version": app.get("version") == version,
        "application_identity": app.get("name") == "QWP-777",
        "declared_dependencies_covered": not missing and not unexpected,
        "dependency_policy_hash_matches": metadata_props.get("qwp777:dependency-policy-sha256") == policy_hash,
        "no_vulnerability_scan_claim": data.get("properties", [{}])[0].get("value") == "not-performed-offline"
            and metadata_props.get("qwp777:lockfile-present") == "false",
    }
    return {"report_schema": "qwp777-sbom-verification-1", "verified": all(checks.values()),
            "components_expected": len(expected), "components_found": len(seen),
            "missing_components": missing, "unexpected_components": unexpected, "checks": checks}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify QWP-777 CycloneDX SBOM.")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate"); gen.add_argument("--root", default="."); gen.add_argument("--output", default="docs/SBOM.cdx.json"); gen.add_argument("--policy", default="DEPENDENCIES.json")
    ver = sub.add_parser("verify"); ver.add_argument("--root", default="."); ver.add_argument("--sbom", default="docs/SBOM.cdx.json"); ver.add_argument("--policy", default="DEPENDENCIES.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            result = create_sbom(args.root, args.output, args.policy)
        else:
            result = verify_sbom(args.root, args.sbom, args.policy)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "verify":
            return 0 if result["verified"] else 1
        return 0
    except (OSError, SbomError, json.JSONDecodeError) as exc:
        print(f"qwp777-sbom: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
