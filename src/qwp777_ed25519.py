"""Optional Ed25519 key utilities for manifest signing.

Requires the third-party `cryptography` package. Private keys should be kept
outside the repository and report archives.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

class Ed25519Error(ValueError):
    pass

def _crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
    except ImportError as exc:
        raise Ed25519Error("Ed25519 requires the optional 'cryptography' package") from exc
    return Ed25519PrivateKey, Ed25519PublicKey, serialization

def generate_key_pair(private_path, public_path, passphrase=None):
    """Create PEM key files without overwriting existing files."""
    _, _, serialization = _crypto()
    private_path, public_path = Path(private_path), Path(public_path)
    if private_path.resolve() == public_path.resolve():
        raise Ed25519Error("private and public key paths must differ")
    if private_path.exists() or public_path.exists():
        raise Ed25519Error("refusing to overwrite an existing key file")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    private = Ed25519PrivateKey.generate()
    encryption = (serialization.BestAvailableEncryption(passphrase.encode("utf-8"))
                  if passphrase else serialization.NoEncryption())
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )
    public_pem = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    try:
        with private_path.open("xb") as stream:
            stream.write(private_pem)
        try:
            private_path.chmod(0o600)
        except OSError:
            pass
        with public_path.open("xb") as stream:
            stream.write(public_pem)
    except FileExistsError as exc:
        # Never remove or overwrite a path that may belong to another process.
        raise Ed25519Error("a key file appeared during generation; no overwrite was performed") from exc
    public_raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return {
        "algorithm": "Ed25519",
        "private_key_path": str(private_path),
        "public_key_path": str(public_path),
        "private_key_encrypted": passphrase is not None,
        "key_id": hashlib.sha256(public_raw).hexdigest(),
        "notes": ["Keep the private key secret and outside source control.",
                  "Distribute the public key separately to archive verifiers."]
    }

def load_private_key(path, password=None):
    _, _, serialization = _crypto()
    try:
        key = serialization.load_pem_private_key(
            Path(path).read_bytes(),
            password=password.encode("utf-8") if isinstance(password, str) else password
        )
    except (OSError, ValueError, TypeError) as exc:
        raise Ed25519Error(f"cannot load Ed25519 private key: {exc}") from exc
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(key, Ed25519PrivateKey):
        raise Ed25519Error("private key file is not an Ed25519 key")
    return key

def load_public_key(path):
    _, _, serialization = _crypto()
    try:
        key = serialization.load_pem_public_key(Path(path).read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise Ed25519Error(f"cannot load Ed25519 public key: {exc}") from exc
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if not isinstance(key, Ed25519PublicKey):
        raise Ed25519Error("public key file is not an Ed25519 key")
    return key

def public_key_id(public_key):
    _, _, serialization = _crypto()
    raw = public_key.public_bytes(encoding=serialization.Encoding.Raw,
                                  format=serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()
