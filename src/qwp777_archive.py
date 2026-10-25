"""Archive reports with SHA-256 checksums and optional HMAC or Ed25519 signatures."""
from __future__ import annotations
import argparse, base64, hashlib, hmac, json, os, re, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

class ArchiveError(ValueError):
    pass

def _sha256(data):
    return hashlib.sha256(data).hexdigest()

def _canonical_manifest(manifest):
    canonical = dict(manifest)
    signature = canonical.get("signature")
    if isinstance(signature, dict):
        canonical["signature"] = {key: value for key, value in signature.items() if key != "value"}
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _load_json_bytes(data, label):
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"cannot parse {label} JSON: {exc}") from exc
    if not isinstance(payload, (dict, list)):
        raise ArchiveError(f"{label} JSON must be an object or array")
    return payload

def _load_optional_ed25519_private(path, password):
    from qwp777_ed25519 import load_private_key, Ed25519Error, public_key_id
    try:
        key = load_private_key(path, password)
        return key, public_key_id(key.public_key())
    except Ed25519Error as exc:
        raise ArchiveError(str(exc)) from exc

def create_report_archive(report_path, config_path, archive_dir="reports/archive",
                          archive_name=None, signing_key=None, key_env="QWP777_ARCHIVE_HMAC_KEY",
                          require_signature=False, ed25519_private_key_path=None,
                          private_key_password=None):
    """Archive report/config, with optional HMAC-SHA256 or Ed25519 manifest signature."""
    report_path, config_path = Path(report_path), Path(config_path)
    try:
        report_bytes = report_path.read_bytes()
        config_bytes = config_path.read_bytes()
    except OSError as exc:
        raise ArchiveError(f"cannot read report/configuration: {exc}") from exc
    report_data = _load_json_bytes(report_bytes, "report")
    config_data = _load_json_bytes(config_bytes, "configuration")
    if signing_key is not None and ed25519_private_key_path is not None:
        raise ArchiveError("choose either HMAC signing_key or Ed25519 private key, not both")
    signing_mode = "ed25519" if ed25519_private_key_path is not None else ("hmac" if signing_key is not None else None)
    if require_signature and signing_mode is None:
        raise ArchiveError("signature required; provide a HMAC secret or Ed25519 private key")
    if signing_mode == "hmac":
        if isinstance(signing_key, str):
            signing_key = signing_key.encode("utf-8")
        if not isinstance(signing_key, bytes) or not signing_key:
            raise ArchiveError("HMAC signing key must be non-empty string or bytes")
    ed_private = None
    ed_key_id = None
    if signing_mode == "ed25519":
        ed_private, ed_key_id = _load_optional_ed25519_private(ed25519_private_key_path, private_key_password)
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    digest_short = _sha256(report_bytes + b"\0" + config_bytes)[:10]
    if archive_name is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_name = f"experiment-{stamp}-{digest_short}"
    if not isinstance(archive_name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", archive_name) or archive_name in {".", ".."}:
        raise ArchiveError("archive_name must use only letters, digits, dot, underscore, or hyphen")
    archive_root = Path(archive_dir)
    folder = archive_root / archive_name
    zip_path = archive_root / f"{archive_name}.zip"
    if folder.exists() or zip_path.exists():
        raise ArchiveError(f"archive already exists: {archive_name}")
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "report.json").write_bytes(report_bytes)
    (folder / "configuration.json").write_bytes(config_bytes)
    manifest = {
        "manifest_schema": "qwp777-archive-manifest-3",
        "archive_name": archive_name,
        "created_utc": created,
        "signature_status": "signed" if signing_mode is not None else "unsigned",
        "files": {
            "report.json": {"sha256": _sha256(report_bytes), "size_bytes": len(report_bytes), "source_path": str(report_path)},
            "configuration.json": {"sha256": _sha256(config_bytes), "size_bytes": len(config_bytes), "source_path": str(config_path)}
        },
        "summary": {
            "report_top_level_type": "object" if isinstance(report_data, dict) else "array",
            "configuration_top_level_type": "object" if isinstance(config_data, dict) else "array"
        },
        "notes": [
            "SHA-256 values identify archived bytes; they do not attest to scientific validity.",
            "HMAC-SHA256 uses a shared secret; Ed25519 signatures can be verified using a public key.",
            "Private signing keys and HMAC secrets are not written into the archive."
        ]
    }
    if signing_mode == "hmac":
        manifest["signature"] = {"algorithm": "HMAC-SHA256", "key_env": key_env, "value": ""}
        manifest["signature"]["value"] = hmac.new(signing_key, _canonical_manifest(manifest), hashlib.sha256).hexdigest()
    elif signing_mode == "ed25519":
        manifest["signature"] = {"algorithm": "Ed25519", "key_id": ed_key_id, "value": ""}
        manifest["signature"]["value"] = base64.b64encode(ed_private.sign(_canonical_manifest(manifest))).decode("ascii")
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    (folder / "manifest.json").write_bytes(manifest_bytes)
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename in ("report.json", "configuration.json", "manifest.json"):
                archive.write(folder / filename, arcname=f"{archive_name}/{filename}")
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
    except (OSError, zipfile.BadZipFile) as exc:
        raise ArchiveError(f"could not build archive: {exc}") from exc
    if bad is not None:
        raise ArchiveError(f"created archive failed integrity check at {bad}")
    return {
        "archive_schema": "qwp777-report-archive-3",
        "archive_name": archive_name, "folder": str(folder), "zip_path": str(zip_path),
        "zip_sha256": _sha256(zip_path.read_bytes()),
        "signature_status": manifest["signature_status"],
        "signature_algorithm": manifest.get("signature", {}).get("algorithm"),
        "manifest": manifest, "zip_integrity": "ok"
    }

def verify_report_archive(zip_path, signing_key=None, public_key_path=None):
    """Verify ZIP CRC, archive manifest, file SHA-256 values, and HMAC or Ed25519 signature."""
    zip_path = Path(zip_path)
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise ArchiveError(f"ZIP CRC/integrity failure at {bad}")
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ArchiveError("archive contains duplicate ZIP member names")
            manifests = [name for name in names if name.endswith("/manifest.json") or name == "manifest.json"]
            if len(manifests) != 1:
                raise ArchiveError("archive must contain exactly one manifest.json")
            manifest_name = manifests[0]
            prefix = manifest_name[:-len("manifest.json")]
            manifest = _load_json_bytes(archive.read(manifest_name), "manifest")
            if not isinstance(manifest, dict) or manifest.get("manifest_schema") not in {
                "qwp777-archive-manifest-2", "qwp777-archive-manifest-3"
            }:
                raise ArchiveError("unsupported archive manifest schema")
            signature = manifest.get("signature")
            if not isinstance(signature, dict):
                raise ArchiveError("manifest is unsigned")
            algorithm = signature.get("algorithm")
            if algorithm == "HMAC-SHA256":
                if public_key_path is not None:
                    raise ArchiveError("HMAC archive verification uses a shared secret, not a public key")
                if signing_key is None:
                    raise ArchiveError("HMAC verification requires the shared signing secret")
                key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
                if not isinstance(key, bytes) or not key:
                    raise ArchiveError("HMAC signing key must be non-empty")
                if manifest.get("signature_status") != "signed":
                    raise ArchiveError("manifest signature status is inconsistent")
                expected = hmac.new(key, _canonical_manifest(manifest), hashlib.sha256).hexdigest()
                supplied = signature.get("value")
                if not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied):
                    raise ArchiveError("manifest signature verification failed")
            elif algorithm == "Ed25519":
                if signing_key is not None:
                    raise ArchiveError("Ed25519 archive verification uses a public key, not an HMAC secret")
                if public_key_path is None:
                    raise ArchiveError("Ed25519 verification requires a public key file")
                try:
                    from qwp777_ed25519 import load_public_key, public_key_id, Ed25519Error
                    public_key = load_public_key(public_key_path)
                    if public_key_id(public_key) != signature.get("key_id"):
                        raise ArchiveError("public key fingerprint does not match the manifest key_id")
                    try:
                        signature_bytes = base64.b64decode(signature.get("value", ""), validate=True)
                    except (ValueError, TypeError) as exc:
                        raise ArchiveError("invalid Ed25519 signature encoding") from exc
                    public_key.verify(signature_bytes, _canonical_manifest(manifest))
                except Ed25519Error as exc:
                    raise ArchiveError(str(exc)) from exc
                except Exception as exc:
                    # Invalid signatures from cryptography are not accepted.
                    if isinstance(exc, ArchiveError):
                        raise
                    raise ArchiveError("Ed25519 signature verification failed") from exc
            else:
                raise ArchiveError("unsupported signature algorithm")
            if manifest.get("signature_status") != "signed":
                raise ArchiveError("manifest signature status is inconsistent")
            verified_files = {}
            files_metadata = manifest.get("files")
            if not isinstance(files_metadata, dict):
                raise ArchiveError("manifest files metadata must be an object")
            for name in ("report.json", "configuration.json"):
                member = prefix + name
                if names.count(member) != 1:
                    raise ArchiveError(f"archive must contain exactly one {name}")
                data = archive.read(member)
                metadata = files_metadata.get(name)
                if not isinstance(metadata, dict):
                    raise ArchiveError(f"manifest missing metadata for {name}")
                if len(data) != metadata.get("size_bytes") or _sha256(data) != metadata.get("sha256"):
                    raise ArchiveError(f"archived {name} does not match its manifest hash")
                _load_json_bytes(data, name)
                verified_files[name] = {"size_bytes": len(data), "sha256": _sha256(data)}
    except zipfile.BadZipFile as exc:
        raise ArchiveError(f"invalid ZIP: {exc}") from exc
    except OSError as exc:
        raise ArchiveError(f"cannot read archive: {exc}") from exc
    return {
        "verification_schema": "qwp777-archive-verification-2",
        "zip_path": str(zip_path), "verified": True,
        "signature_algorithm": algorithm,
        "archive_name": manifest.get("archive_name"),
        "files": verified_files,
        "notes": ["A valid signature verifies archive integrity/authenticity for the specified key trust model, not scientific correctness."]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Archive a report/configuration; optionally authenticate manifest with HMAC-SHA256 or Ed25519.")
    parser.add_argument("report", help="report JSON file")
    parser.add_argument("--config", required=True, help="input configuration JSON file")
    parser.add_argument("--archive-dir", default="reports/archive", help="archive output directory")
    parser.add_argument("--name", help="optional unique archive name")
    parser.add_argument("--key-env", default="QWP777_ARCHIVE_HMAC_KEY", help="environment variable holding HMAC secret")
    parser.add_argument("--ed25519-private-key", help="Ed25519 private key PEM; secret file must stay private")
    parser.add_argument("--private-key-password-env", help="environment variable for encrypted private-key passphrase")
    parser.add_argument("--require-signature", action="store_true", help="fail unless a signature is supplied")
    parser.add_argument("-o", "--output", help="write archive summary JSON to path")
    args = parser.parse_args(argv)
    try:
        signing_key = os.environ.get(args.key_env) if not args.ed25519_private_key else None
        password = os.environ.get(args.private_key_password_env) if args.private_key_password_env else None
        result = create_report_archive(
            args.report, args.config, args.archive_dir, args.name,
            signing_key=signing_key, key_env=args.key_env,
            require_signature=args.require_signature,
            ed25519_private_key_path=args.ed25519_private_key,
            private_key_password=password
        )
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, ArchiveError, zipfile.BadZipFile) as exc:
        print(f"qwp777-archive: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
