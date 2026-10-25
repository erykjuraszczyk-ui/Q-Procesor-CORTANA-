import hashlib, json, sys, tempfile, unittest, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_archive import create_report_archive, verify_report_archive, ArchiveError

class V17SignedArchiveTests(unittest.TestCase):
    def _inputs(self, folder):
        report = folder/"report.json"
        config = folder/"config.json"
        report.write_text('{"report_schema":"demo-report"}\n')
        config.write_text('{"num_qubits":1,"gates":[{"gate":"MEASURE","qubits":[0]}]}\n')
        return report, config

    def test_signed_archive_verifies(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            report, config = self._inputs(folder)
            created = create_report_archive(report, config, folder/"archives", "signed-case",
                                           signing_key="a-long-test-secret")
            self.assertEqual(created["signature_status"], "signed")
            verified = verify_report_archive(created["zip_path"], "a-long-test-secret")
            self.assertTrue(verified["verified"])

    def test_wrong_key_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            report, config = self._inputs(folder)
            created = create_report_archive(report, config, folder/"archives", "signed-case",
                                           signing_key="correct-secret")
            with self.assertRaises(ArchiveError):
                verify_report_archive(created["zip_path"], "wrong-secret")

    def test_unsigned_archive_cannot_pass_signature_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            report, config = self._inputs(folder)
            created = create_report_archive(report, config, folder/"archives", "unsigned-case")
            self.assertEqual(created["signature_status"], "unsigned")
            with self.assertRaises(ArchiveError):
                verify_report_archive(created["zip_path"], "any-secret")

    def test_tampered_manifest_or_payload_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            report, config = self._inputs(folder)
            created = create_report_archive(report, config, folder/"archives", "signed-case",
                                           signing_key="test-secret")
            tampered = folder/"tampered.zip"
            with zipfile.ZipFile(created["zip_path"]) as old, zipfile.ZipFile(tampered, "w") as new:
                for name in old.namelist():
                    data = old.read(name)
                    if name.endswith("/report.json"):
                        data = b'{"tampered":true}\n'
                    new.writestr(name, data)
            with self.assertRaises(ArchiveError):
                verify_report_archive(tampered, "test-secret")


    def test_signature_metadata_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            report, config = self._inputs(folder)
            created = create_report_archive(report, config, folder/"archives", "signed-case",
                                           signing_key="test-secret", key_env="TEST_KEY")
            tampered = folder/"tampered-metadata.zip"
            with zipfile.ZipFile(created["zip_path"]) as old, zipfile.ZipFile(tampered, "w") as new:
                for name in old.namelist():
                    data = old.read(name)
                    if name.endswith("/manifest.json"):
                        manifest = json.loads(data)
                        manifest["signature"]["key_env"] = "OTHER_KEY"
                        data = json.dumps(manifest, indent=2).encode()
                    new.writestr(name, data)
            with self.assertRaises(ArchiveError):
                verify_report_archive(tampered, "test-secret")

if __name__ == "__main__":
    unittest.main()
