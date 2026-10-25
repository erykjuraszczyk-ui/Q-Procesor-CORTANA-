import json, os, sys, tempfile, unittest, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_ed25519 import generate_key_pair, Ed25519Error
from qwp777_archive import create_report_archive, verify_report_archive, ArchiveError

try:
    import cryptography  # noqa: F401
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

@unittest.skipUnless(CRYPTOGRAPHY_AVAILABLE, "optional cryptography package is not installed")
class V18Ed25519Tests(unittest.TestCase):
    def _inputs(self, folder):
        report = folder/"report.json"
        config = folder/"config.json"
        report.write_text('{"report_schema":"test-report"}\n')
        config.write_text('{"num_qubits":1,"gates":[{"gate":"MEASURE","qubits":[0]}]}\n')
        return report, config

    def test_keypair_and_signed_archive_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            private=folder/"private.pem"; public=folder/"public.pem"
            generated=generate_key_pair(private, public, passphrase="test-passphrase")
            self.assertTrue(private.exists() and public.exists())
            self.assertTrue(generated["private_key_encrypted"])
            report, config = self._inputs(folder)
            archive=create_report_archive(report, config, folder/"archives", "ed-case",
                ed25519_private_key_path=private, private_key_password="test-passphrase", require_signature=True)
            self.assertEqual(archive["signature_algorithm"], "Ed25519")
            verify=verify_report_archive(archive["zip_path"], public_key_path=public)
            self.assertTrue(verify["verified"])
            self.assertEqual(verify["signature_algorithm"], "Ed25519")

    def test_wrong_public_key_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            private=folder/"private.pem"; public=folder/"public.pem"
            other_private=folder/"other-private.pem"; other_public=folder/"other-public.pem"
            generate_key_pair(private, public)
            generate_key_pair(other_private, other_public)
            report, config = self._inputs(folder)
            archive=create_report_archive(report, config, folder/"archives", "ed-case",
                ed25519_private_key_path=private, require_signature=True)
            with self.assertRaises(ArchiveError):
                verify_report_archive(archive["zip_path"], public_key_path=other_public)

    def test_ed25519_refuses_overwrite_key_files(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            private=folder/"private.pem"; public=folder/"public.pem"
            private.write_text("preserve")
            with self.assertRaises(Ed25519Error):
                generate_key_pair(private, public)
            self.assertEqual(private.read_text(), "preserve")

    def test_invalid_private_key_password_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            private=folder/"private.pem"; public=folder/"public.pem"
            generate_key_pair(private, public, passphrase="right")
            report, config = self._inputs(folder)
            with self.assertRaises(ArchiveError):
                create_report_archive(report, config, folder/"archives", "ed-case",
                    ed25519_private_key_path=private, private_key_password="wrong", require_signature=True)


    def test_ed25519_key_id_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            private=folder/"private.pem"; public=folder/"public.pem"
            generate_key_pair(private, public)
            report, config = self._inputs(folder)
            created=create_report_archive(report, config, folder/"archives", "ed-case",
                ed25519_private_key_path=private, require_signature=True)
            tampered=folder/"tampered-key-id.zip"
            with zipfile.ZipFile(created["zip_path"]) as old, zipfile.ZipFile(tampered, "w") as new:
                for name in old.namelist():
                    data=old.read(name)
                    if name.endswith("/manifest.json"):
                        manifest=json.loads(data)
                        manifest["signature"]["key_id"]="0"*64
                        data=json.dumps(manifest, indent=2).encode()
                    new.writestr(name, data)
            with self.assertRaises(ArchiveError):
                verify_report_archive(tampered, public_key_path=public)

if __name__ == "__main__":
    unittest.main()
