"""Ed25519 signing and verification for exact QWP-777 release-manifest bytes.

The detached signature is distributed separately from the ZIP and manifest.
A verifier must trust the provided public key through an independent channel.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from qwp777_ed25519 import (
    Ed25519Error, generate_key_pair, load_private_key, load_public_key, public_key_id,
)

SIGNATURE_SCHEMA = "qwp777-manifest-signature-1"

class ReleaseSignatureError(ValueError):
    """Raised when a manifest signature cannot be created or verified."""

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sign_manifest(manifest_path, private_key_path, output_path, password=None):
    manifest = Path(manifest_path)
    output = Path(output_path)
    if not manifest.is_file():
        raise ReleaseSignatureError(f"manifest does not exist: {manifest}")
    if output.exists():
        raise ReleaseSignatureError(f"signature output already exists; refusing overwrite: {output}")
    try:
        raw = manifest.read_bytes()
        manifest_object = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseSignatureError(f"cannot read manifest JSON: {exc}") from exc
    if manifest_object.get("manifest_schema") != "qwp777-release-manifest-1":
        raise ReleaseSignatureError("unsupported release manifest schema")
    try:
        private = load_private_key(private_key_path, password=password)
        signature = private.sign(raw)
        key_id = public_key_id(private.public_key())
    except Ed25519Error as exc:
        raise ReleaseSignatureError(str(exc)) from exc
    envelope = {
        "signature_schema": SIGNATURE_SCHEMA,
        "algorithm": "Ed25519",
        "signed_file": manifest.name,
        "release": manifest_object.get("software", {}).get("release"),
        "manifest_sha256": _sha256(raw),
        "manifest_size_bytes": len(raw),
        "key_id_sha256": key_id,
        "signature_base64": base64.b64encode(signature).decode("ascii"),
        "signed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trust_note": "A valid signature proves the manifest was signed by the private key matching the supplied public key; publisher identity requires an independently trusted key."
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as stream:
            json.dump(envelope, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except FileExistsError as exc:
        raise ReleaseSignatureError(f"signature output appeared during signing: {output}") from exc
    return {"signed": True, "release": envelope["release"], "algorithm": "Ed25519",
            "manifest_sha256": envelope["manifest_sha256"], "key_id_sha256": key_id,
            "signature_path": str(output)}

def verify_manifest_signature(manifest_path, signature_path, public_key_path):
    manifest, signature_file = Path(manifest_path), Path(signature_path)
    try:
        raw = manifest.read_bytes()
        envelope = json.loads(signature_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseSignatureError(f"cannot read manifest or signature file: {exc}") from exc
    if envelope.get("signature_schema") != SIGNATURE_SCHEMA or envelope.get("algorithm") != "Ed25519":
        raise ReleaseSignatureError("unsupported signature schema or algorithm")
    if envelope.get("signed_file") != manifest.name:
        raise ReleaseSignatureError("signature names a different manifest file")
    digest = _sha256(raw)
    if envelope.get("manifest_sha256") != digest or envelope.get("manifest_size_bytes") != len(raw):
        raise ReleaseSignatureError("manifest digest or size does not match the signed envelope")
    try:
        manifest_object = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseSignatureError(f"manifest is not valid UTF-8 JSON: {exc}") from exc
    if manifest_object.get("manifest_schema") != "qwp777-release-manifest-1":
        raise ReleaseSignatureError("unsupported release manifest schema")
    if envelope.get("release") != manifest_object.get("software", {}).get("release"):
        raise ReleaseSignatureError("signature release does not match manifest release")
    try:
        signature = base64.b64decode(envelope.get("signature_base64", ""), validate=True)
        public = load_public_key(public_key_path)
        key_id = public_key_id(public)
        if envelope.get("key_id_sha256") != key_id:
            raise ReleaseSignatureError("public key ID does not match signature envelope")
        public.verify(signature, raw)
    except ReleaseSignatureError:
        raise
    except Exception as exc:
        raise ReleaseSignatureError(f"Ed25519 signature verification failed: {exc}") from exc
    return {"verified": True, "release": envelope.get("release"), "algorithm": "Ed25519",
            "manifest_sha256": digest, "key_id_sha256": key_id,
            "trust_note": "Cryptographic validity does not by itself establish publisher identity; independently verify the public-key fingerprint."}

def main(argv=None):
    parser = argparse.ArgumentParser(description="Sign or verify QWP-777 release manifests with Ed25519.")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("keygen", help="generate a new Ed25519 key pair")
    gen.add_argument("--private-key", required=True)
    gen.add_argument("--public-key", required=True)
    gen.add_argument("--passphrase-env", help="environment variable containing private-key passphrase")
    sign = sub.add_parser("sign", help="sign exact manifest bytes")
    sign.add_argument("--manifest", required=True)
    sign.add_argument("--private-key", required=True)
    sign.add_argument("--password-env", help="environment variable containing private-key passphrase")
    sign.add_argument("--output", required=True, help="detached signature JSON output")
    verify = sub.add_parser("verify", help="verify manifest signature and key ID")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--signature", required=True)
    verify.add_argument("--public-key", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            password = os.environ.get(args.passphrase_env) if args.passphrase_env else None
            if args.passphrase_env and not password:
                raise ReleaseSignatureError("private key passphrase environment variable is empty or missing")
            result = generate_key_pair(args.private_key, args.public_key, password)
        elif args.command == "sign":
            password = os.environ.get(args.password_env) if args.password_env else None
            if args.password_env and not password:
                raise ReleaseSignatureError("private key password environment variable is empty or missing")
            result = sign_manifest(args.manifest, args.private_key, args.output, password)
        else:
            result = verify_manifest_signature(args.manifest, args.signature, args.public_key)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("verified", result.get("signed", True)) else 1
    except (OSError, Ed25519Error, ReleaseSignatureError) as exc:
        print(f"qwp777-release-signing: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
