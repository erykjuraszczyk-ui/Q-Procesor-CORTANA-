import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_ed25519 import generate_key_pair
from qwp777_release_package import create_manifest
from qwp777_release_signing import sign_manifest, verify_manifest_signature, ReleaseSignatureError

try:
    import cryptography  # noqa: F401
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

@unittest.skipUnless(CRYPTOGRAPHY_AVAILABLE, "optional cryptography package is not installed")
class ReleaseSigningTests(unittest.TestCase):
    def _release(self, root):
        (root / "docs").mkdir()
        (root / "VERSION").write_text("3.1.0\n", encoding="utf-8")
        (root / "README.md").write_text("signed test release\n", encoding="utf-8")
        return create_manifest(root)

    def test_manifest_signature_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "release"; root.mkdir()
            self._release(root)
            private, public = Path(tmp)/"private.pem", Path(tmp)/"public.pem"
            generate_key_pair(private, public)
            sig = Path(tmp)/"manifest.sig.json"
            signed = sign_manifest(root/"docs/RELEASE_MANIFEST.json", private, sig)
            self.assertTrue(signed["signed"])
            verified = verify_manifest_signature(root/"docs/RELEASE_MANIFEST.json", sig, public)
            self.assertTrue(verified["verified"])
            self.assertEqual(verified["algorithm"], "Ed25519")

    def test_tampered_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"release"; root.mkdir(); self._release(root)
            private, public, sig = Path(tmp)/"private.pem", Path(tmp)/"public.pem", Path(tmp)/"sig.json"
            generate_key_pair(private, public)
            manifest = root/"docs/RELEASE_MANIFEST.json"
            sign_manifest(manifest, private, sig)
            manifest.write_text(manifest.read_text()+" ", encoding="utf-8")
            with self.assertRaises(ReleaseSignatureError):
                verify_manifest_signature(manifest, sig, public)

    def test_wrong_public_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"release"; root.mkdir(); self._release(root)
            private, public = Path(tmp)/"private.pem", Path(tmp)/"public.pem"
            wrong_private, wrong_public = Path(tmp)/"wrong-private.pem", Path(tmp)/"wrong-public.pem"
            generate_key_pair(private, public); generate_key_pair(wrong_private, wrong_public)
            sig = Path(tmp)/"sig.json"
            sign_manifest(root/"docs/RELEASE_MANIFEST.json", private, sig)
            with self.assertRaises(ReleaseSignatureError):
                verify_manifest_signature(root/"docs/RELEASE_MANIFEST.json", sig, wrong_public)

    def test_signature_output_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"release"; root.mkdir(); self._release(root)
            private, public, sig = Path(tmp)/"private.pem", Path(tmp)/"public.pem", Path(tmp)/"sig.json"
            generate_key_pair(private, public); sig.write_text("preserve", encoding="utf-8")
            with self.assertRaises(ReleaseSignatureError):
                sign_manifest(root/"docs/RELEASE_MANIFEST.json", private, sig)
            self.assertEqual(sig.read_text(encoding="utf-8"), "preserve")

if __name__ == "__main__":
    unittest.main()
