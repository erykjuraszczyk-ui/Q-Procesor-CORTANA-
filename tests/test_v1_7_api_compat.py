import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_api_compat import check_api_compatibility, ApiCompatibilityError

class V17ApiCompatibilityTests(unittest.TestCase):
    def test_v16_contract_is_compatible(self):
        report = check_api_compatibility()
        self.assertTrue(report["compatible"], report)
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["contract"]["snapshot_release"], "1.6.0")

    def test_missing_legacy_export_is_reported(self):
        contract = Path(__file__).resolve().parents[1] / "compatibility" / "api-v1.6.0.json"
        fixture = json.loads(contract.read_text())
        fixture["public_exports"].append("removed_legacy_symbol")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"contract.json"
            path.write_text(json.dumps(fixture))
            report = check_api_compatibility(path)
        self.assertFalse(report["compatible"])
        self.assertIn("removed_legacy_symbol", report["missing_exports"])

    def test_wrong_contract_schema_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"contract.json"
            path.write_text(json.dumps({"compatibility_schema":"unknown"}))
            with self.assertRaises(ApiCompatibilityError):
                check_api_compatibility(path)

if __name__ == "__main__":
    unittest.main()
