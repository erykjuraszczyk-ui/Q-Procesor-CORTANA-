"""Offline static audit of declared optional dependencies and source imports.

This tool does not query an online CVE/advisory database and cannot conclude
that any component is vulnerability-free.
"""
from __future__ import annotations
import argparse
import ast
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from qwp777_sbom import verify_sbom, SbomError

class DependencyAuditError(ValueError):
    pass

def _source_imports(root: Path) -> set[str]:
    source = root / "src"
    internal = {p.stem for p in source.glob("*.py")}
    found: set[str] = set()
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    for path in source.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            raise DependencyAuditError(f"cannot parse source imports in {path}: {exc}") from exc
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".", 1)[0]]
            for name in names:
                if name and name not in stdlib and name not in internal and not name.startswith("qwp777"):
                    found.add(name)
    return found

def audit_dependencies(root: str | Path, sbom_path: str | Path = "docs/SBOM.cdx.json",
                       policy_path: str | Path = "DEPENDENCIES.json") -> dict:
    root = Path(root).resolve()
    try:
        policy = json.loads((root / policy_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyAuditError(f"cannot read dependency policy: {exc}") from exc
    if policy.get("dependency_policy_schema") != "qwp777-dependency-policy-1":
        raise DependencyAuditError("unsupported dependency policy schema")
    expected_imports = {}
    for dep in policy.get("optional_dependencies", []):
        for imported in dep.get("import_names", []):
            expected_imports[imported] = dep
    imports = _source_imports(root)
    undeclared = sorted(imports - set(expected_imports))
    sbom = verify_sbom(root, sbom_path, policy_path)
    observed = []
    for dep in policy.get("optional_dependencies", []):
        try:
            version = importlib.metadata.version(dep["distribution"])
            installed = True
        except importlib.metadata.PackageNotFoundError:
            version, installed = None, False
        observed.append({"name": dep["name"], "distribution": dep["distribution"],
                         "scope": dep.get("scope", "optional"), "installed_in_build_environment": installed,
                         "observed_version": version, "version_constraint": dep.get("version_constraint"),
                         "feature": dep.get("feature")})
    vuln = policy.get("security_assessment", {})
    report = {
        "report_schema": "qwp777-dependency-audit-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {"name": "QWP-777", "release": (root / "VERSION").read_text(encoding="utf-8").strip()},
        "summary": {"passed": not undeclared and sbom.get("verified") is True,
                    "source_imports_found": len(imports), "declared_imports": len(set(expected_imports)),
                    "undeclared_imports": undeclared,
                    "sbom_verified": sbom.get("verified") is True,
                    "optional_dependencies_total": len(observed),
                    "optional_dependencies_installed_in_build_environment": sum(x["installed_in_build_environment"] for x in observed)},
        "source_import_modules": sorted(imports),
        "optional_dependencies": observed,
        "sbom_verification": sbom,
        "security_assessment": {
            "mode": vuln.get("mode", "offline-static"),
            "live_vulnerability_database_used": False,
            "vulnerability_status": "not_assessed",
            "vulnerability_scan_performed": False,
            "note": vuln.get("note", "No live CVE/advisory scan was performed.")
        },
        "caveats": [
            "This report checks dependency declarations and source-import coverage only.",
            "No CVE, OSV, vendor advisory, malware, or license service was queried.",
            "Versions observed in the build environment do not pin or describe every target environment."
        ]
    }
    return report

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run QWP-777's offline dependency declaration audit.")
    parser.add_argument("--root", default="."); parser.add_argument("--sbom", default="docs/SBOM.cdx.json")
    parser.add_argument("--policy", default="DEPENDENCIES.json"); parser.add_argument("-o", "--output", default="docs/DEPENDENCY_AUDIT.json")
    args = parser.parse_args(argv)
    try:
        report = audit_dependencies(args.root, args.sbom, args.policy)
        out = Path(args.output)
        if not out.is_absolute(): out = Path(args.root).resolve() / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["summary"]["passed"] else 1
    except (OSError, DependencyAuditError, SbomError) as exc:
        print(f"qwp777-dependency-audit: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
