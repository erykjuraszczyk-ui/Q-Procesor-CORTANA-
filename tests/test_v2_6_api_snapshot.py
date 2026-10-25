import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import qwp777_api
from qwp777_api_compat import check_api_compatibility
from qwp777_version import RESULT_SCHEMA_VERSION

class V26ApiSnapshotTests(unittest.TestCase):
    def test_frozen_v26_contract_remains_readable_and_compatible(self):
        contract_path = ROOT / "compatibility" / "api-v2.6.0.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        report = check_api_compatibility(contract_path)
        self.assertTrue(report["compatible"], report)
        self.assertEqual(contract["snapshot_release"], "2.6.0")
        self.assertEqual(contract["snapshot_api_version"], "2.6")
        self.assertEqual(RESULT_SCHEMA_VERSION, contract["experiment_result_schema"])

    def test_legacy_contracts_remain_compatible(self):
        for contract in ("api-v1.6.0.json", "api-v2.0.0.json", "api-v2.1.0.json", "api-v2.2.0.json", "api-v2.3.0.json", "api-v2.4.0.json", "api-v2.5.0.json", "api-v2.6.0.json"):
            report = check_api_compatibility(ROOT / "compatibility" / contract)
            self.assertTrue(report["compatible"], (contract, report))

if __name__ == "__main__":
    unittest.main()
