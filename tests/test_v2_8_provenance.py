import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_provenance import create_provenance, verify_provenance, ProvenanceError

class ProvenanceTests(unittest.TestCase):
    def _root(self, base):
        root = Path(base)/"release"
        for folder in ("docs", "compatibility", "regression/baselines"):
            (root/folder).mkdir(parents=True, exist_ok=True)
        (root/"VERSION").write_text("3.1.0\n", encoding="utf-8")
        (root/"compatibility/api-v3.1.0.json").write_text('{"snapshot_release":"3.1.0"}\n', encoding="utf-8")
        (root/"regression/baselines/v3.1.0.json").write_text('{"baseline_release":"3.1.0"}\n', encoding="utf-8")
        (root/"docs/RELEASE_AUDIT.json").write_text(json.dumps({"summary":{"passed":True,"checks_passed":19,"checks_total":19},"unit_tests":{"tests_run":170}}), encoding="utf-8")
        (root/"docs/TEST_REPORT.json").write_text(json.dumps({"report_schema":"test-report-v1"}), encoding="utf-8")
        return root

    def test_provenance_creation_and_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            report = create_provenance(root, source_release="2.7.0")
            self.assertEqual(report["provenance_schema"], "qwp777-build-provenance-1")
            result = verify_provenance(root)
            self.assertTrue(result["verified"], result)
            self.assertEqual(result["inputs_checked"], 4)

    def test_changed_input_report_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            create_provenance(root)
            (root/"docs/TEST_REPORT.json").write_text('{"tampered":true}', encoding="utf-8")
            result = verify_provenance(root)
            self.assertFalse(result["verified"])
            self.assertTrue(any("test_report" == item.get("input") for item in result["failures"]))

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            with self.assertRaises(ProvenanceError):
                create_provenance(root, audit_report="../outside.json")

    def test_source_archive_digest_checked_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            src = Path(tmp)/"Qwantum-Processor-777-v2.7.0.zip"
            src.write_bytes(b"source archive bytes")
            create_provenance(root, source_release="2.7.0", source_archive=src)
            self.assertTrue(verify_provenance(root, source_archive=src)["verified"])
            src.write_bytes(b"modified")
            result = verify_provenance(root, source_archive=src)
            self.assertFalse(result["verified"])
            self.assertTrue(any(item.get("input") == "source_archive" for item in result["failures"]))

if __name__ == "__main__":
    unittest.main()
