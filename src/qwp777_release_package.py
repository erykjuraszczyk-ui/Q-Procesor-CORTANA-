"""Create and verify QWP-777 release manifests and ZIP packages.

The manifest hashes every regular project file except itself. The ZIP's own
SHA-256 is written as an external .sha256 sidecar, avoiding self-reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from qwp777_version import __version__, API_VERSION

MANIFEST_SCHEMA = "qwp777-release-manifest-1"
DEFAULT_MANIFEST = "docs/RELEASE_MANIFEST.json"


class ReleasePackageError(ValueError):
    """Raised when a release manifest or package fails validation."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _excluded(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc" or ".git" in path.parts


def _project_files(root: Path, manifest_rel: str) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or _excluded(path):
            continue
        rel = _manifest_rel(path, root)
        if rel == manifest_rel:
            continue
        if path.is_symlink():
            raise ReleasePackageError(f"symlink files are not allowed in release packages: {rel}")
        files.append(path)
    return sorted(files, key=lambda p: _manifest_rel(p, root))


def create_manifest(root: str | Path, manifest_path: str | Path | None = None) -> dict:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ReleasePackageError(f"release root is not a directory: {root_path}")
    manifest = Path(manifest_path) if manifest_path else root_path / DEFAULT_MANIFEST
    if not manifest.is_absolute():
        manifest = root_path / manifest
    manifest = manifest.resolve()
    try:
        manifest_rel = _manifest_rel(manifest, root_path)
    except ValueError as exc:
        raise ReleasePackageError("manifest must be located inside the release root") from exc
    if manifest_rel in {"", "."}:
        raise ReleasePackageError("manifest path must name a file")

    version_file = root_path / "VERSION"
    if not version_file.is_file():
        raise ReleasePackageError("release root does not contain VERSION")
    version = version_file.read_text(encoding="utf-8").strip()
    if version != __version__:
        raise ReleasePackageError(f"VERSION ({version}) does not match packaged tool version ({__version__})")

    records = []
    for path in _project_files(root_path, manifest_rel):
        raw = path.read_bytes()
        records.append({"path": _manifest_rel(path, root_path), "size_bytes": len(raw), "sha256": _sha256(raw)})
    if not records:
        raise ReleasePackageError("refusing to create an empty release manifest")

    payload = {
        "manifest_schema": MANIFEST_SCHEMA,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {"release": version, "api_version": API_VERSION},
        "manifest_path": manifest_rel,
        "hash_algorithm": "SHA-256",
        "self_hashing": False,
        "files_total": len(records),
        "total_bytes": sum(item["size_bytes"] for item in records),
        "files": records,
        "caveats": [
            "The manifest does not hash itself; this avoids a self-referential digest.",
            "The outer ZIP is authenticated for integrity by the detached .sha256 sidecar.",
            "SHA-256 integrity checks do not authenticate the publisher without a trusted digital signature."
        ]
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def verify_manifest(root: str | Path, manifest_path: str | Path | None = None) -> dict:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ReleasePackageError(f"release root is not a directory: {root_path}")
    manifest = Path(manifest_path) if manifest_path else root_path / DEFAULT_MANIFEST
    if not manifest.is_absolute():
        manifest = root_path / manifest
    manifest = manifest.resolve()
    try:
        manifest_rel = _manifest_rel(manifest, root_path)
    except ValueError as exc:
        raise ReleasePackageError("manifest must be located inside the release root") from exc
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleasePackageError(f"cannot read manifest: {exc}") from exc
    if payload.get("manifest_schema") != MANIFEST_SCHEMA:
        raise ReleasePackageError("unsupported manifest schema")
    if payload.get("manifest_path") != manifest_rel:
        raise ReleasePackageError("manifest_path does not match actual manifest location")
    version = (root_path / "VERSION").read_text(encoding="utf-8").strip()
    if payload.get("software", {}).get("release") != version:
        raise ReleasePackageError("manifest release version does not match VERSION")
    records = payload.get("files")
    if not isinstance(records, list) or not records:
        raise ReleasePackageError("manifest files must be a non-empty list")

    expected: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ReleasePackageError("manifest file record must be an object")
        rel = record.get("path")
        if not isinstance(rel, str) or not rel:
            raise ReleasePackageError("manifest file path must be a non-empty string")
        posix = PurePosixPath(rel)
        if posix.is_absolute() or ".." in posix.parts or "\\" in rel or rel in {".", ""}:
            raise ReleasePackageError(f"unsafe manifest path: {rel}")
        if rel == manifest_rel or rel in expected:
            raise ReleasePackageError(f"duplicate or self-referential manifest record: {rel}")
        expected[rel] = record

    actual_paths = {_manifest_rel(p, root_path) for p in _project_files(root_path, manifest_rel)}
    expected_paths = set(expected)
    missing = sorted(expected_paths - actual_paths)
    unexpected = sorted(actual_paths - expected_paths)
    mismatches = []
    if not missing and not unexpected:
        for rel, record in expected.items():
            path = root_path / PurePosixPath(rel)
            raw = path.read_bytes()
            if record.get("size_bytes") != len(raw) or record.get("sha256") != _sha256(raw):
                mismatches.append(rel)
    ok = not missing and not unexpected and not mismatches
    return {
        "report_schema": "qwp777-release-manifest-verification-1",
        "verified": ok,
        "release": version,
        "manifest_path": manifest_rel,
        "files_expected": len(expected_paths),
        "files_actual": len(actual_paths),
        "missing_files": missing,
        "unexpected_files": unexpected,
        "hash_or_size_mismatches": sorted(mismatches),
    }


def build_archive(root: str | Path, archive_path: str | Path, manifest_path: str | Path | None = None) -> dict:
    root_path = Path(root).resolve()
    archive = Path(archive_path).resolve()
    try:
        archive.relative_to(root_path)
    except ValueError:
        pass
    else:
        raise ReleasePackageError("ZIP output must be outside the release root")
    manifest = create_manifest(root_path, manifest_path)
    verification = verify_manifest(root_path, manifest_path)
    if not verification["verified"]:
        raise ReleasePackageError(f"manifest verification failed: {verification}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(root_path.rglob("*")):
            if path.is_file() and not _excluded(path):
                if path.is_symlink():
                    raise ReleasePackageError(f"symlink files are not allowed in release packages: {path}")
                zf.write(path, Path(root_path.name) / path.relative_to(root_path))
    with zipfile.ZipFile(archive, "r") as zf:
        corrupt_member = zf.testzip()
        if corrupt_member is not None:
            raise ReleasePackageError(f"ZIP CRC test failed for member: {corrupt_member}")
    digest = _sha256(archive.read_bytes())
    sidecar = Path(str(archive) + ".sha256")
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return {
        "report_schema": "qwp777-release-package-build-1",
        "release": manifest["software"]["release"],
        "manifest_verified": verification["verified"],
        "manifest_files_total": manifest["files_total"],
        "archive_path": str(archive),
        "archive_size_bytes": archive.stat().st_size,
        "archive_sha256": digest,
        "sidecar_path": str(sidecar),
        "zip_integrity": "passed"
    }


def verify_archive(archive_path: str | Path, sidecar_path: str | Path | None = None) -> dict:
    archive = Path(archive_path).resolve()
    sidecar = Path(sidecar_path).resolve() if sidecar_path else Path(str(archive) + ".sha256")
    if not archive.is_file():
        raise ReleasePackageError(f"archive does not exist: {archive}")
    try:
        actual = _sha256(archive.read_bytes())
        expected_fields = sidecar.read_text(encoding="utf-8").strip().split()
    except OSError as exc:
        raise ReleasePackageError(f"cannot read archive or SHA-256 sidecar: {exc}") from exc
    if len(expected_fields) < 1 or expected_fields[0].lower() != actual:
        return {"verified": False, "archive_path": str(archive), "sha256_actual": actual,
                "sha256_expected": expected_fields[0] if expected_fields else None,
                "reason": "SHA-256 mismatch"}
    if len(expected_fields) >= 2 and expected_fields[-1].lstrip("*") != archive.name:
        return {"verified": False, "archive_path": str(archive), "sha256_actual": actual,
                "sha256_expected": expected_fields[0], "reason": "sidecar filename mismatch"}
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            corrupt_member = zf.testzip()
    except (OSError, zipfile.BadZipFile) as exc:
        return {"verified": False, "archive_path": str(archive), "sha256_actual": actual,
                "sha256_expected": expected_fields[0], "reason": f"invalid ZIP: {exc}"}
    return {"verified": corrupt_member is None, "archive_path": str(archive), "sha256_actual": actual,
            "sha256_expected": expected_fields[0], "reason": None if corrupt_member is None else f"CRC failure: {corrupt_member}"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build and verify QWP-777 release manifests and ZIP packages.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_manifest = sub.add_parser("manifest", help="create a file manifest")
    p_manifest.add_argument("--root", default=".")
    p_manifest.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p_verify = sub.add_parser("verify", help="verify every file against a manifest")
    p_verify.add_argument("--root", default=".")
    p_verify.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p_build = sub.add_parser("build", help="create manifest, ZIP, and detached SHA-256")
    p_build.add_argument("--root", default=".")
    p_build.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p_build.add_argument("--zip-output", required=True)
    p_archive = sub.add_parser("verify-archive", help="check ZIP CRC and detached SHA-256")
    p_archive.add_argument("archive")
    p_archive.add_argument("--sidecar")
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            result = create_manifest(args.root, args.manifest)
        elif args.command == "verify":
            result = verify_manifest(args.root, args.manifest)
        elif args.command == "build":
            result = build_archive(args.root, args.zip_output, args.manifest)
        else:
            result = verify_archive(args.archive, args.sidecar)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "verify":
            return 0 if result["verified"] else 1
        if args.command == "verify-archive":
            return 0 if result["verified"] else 1
        return 0
    except (OSError, ReleasePackageError, zipfile.BadZipFile) as exc:
        print(f"qwp777-release-package: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
