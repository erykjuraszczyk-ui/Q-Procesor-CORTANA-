import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import qwp777_api
from qwp777_api_compat import check_api_compatibility
from qwp777_version import RESULT_SCHEMA_VERSION


class HistoricalV22ApiContractTests(unittest.TestCase):
    def test_current_public_api_remains_compatible_with_frozen_v22_contract(self):
        contract_path = ROOT / "compatibility" / "api-v2.2.0.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        report = check_api_compatibility(contract_path)
        self.assertTrue(report["compatible"], report)
        self.assertTrue(report["compatible"])
        self.assertEqual(contract["snapshot_release"], "2.2.0")
        self.assertEqual(contract["snapshot_api_version"], "2.2")
        self.assertEqual(RESULT_SCHEMA_VERSION, contract["experiment_result_schema"])

    def test_legacy_v16_public_api_remains_compatible(self):
        report = check_api_compatibility(ROOT / "compatibility" / "api-v1.6.0.json")
        self.assertTrue(report["compatible"], report)

    def test_current_release_differs_from_historical_v22_snapshot(self):
        self.assertEqual(qwp777_api.__version__, "3.1.0")
        self.assertEqual(qwp777_api.API_VERSION, "3.0")


if __name__ == "__main__":
    unittest.main()
