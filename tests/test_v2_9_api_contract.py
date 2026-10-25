import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import qwp777_api
from qwp777_api_compat import check_api_compatibility
from qwp777_version import RESULT_SCHEMA_VERSION

class V29ApiContractTests(unittest.TestCase):
    def test_current_public_api_matches_frozen_v29_contract(self):
        path = ROOT / "compatibility" / "api-v3.1.0.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        report = check_api_compatibility(path)
        self.assertTrue(report["compatible"], report)
        self.assertEqual(qwp777_api.__version__, "3.1.0")
        self.assertEqual(qwp777_api.API_VERSION, "3.0")
        self.assertEqual(RESULT_SCHEMA_VERSION, contract["experiment_result_schema"])
        self.assertEqual(contract["experiment_result_schema"], "qwp777-experiment-1")

    def test_historical_contracts_remain_compatible(self):
        names = ["api-v1.6.0.json", "api-v2.0.0.json", "api-v2.1.0.json", "api-v2.2.0.json",
                 "api-v2.3.0.json", "api-v2.4.0.json", "api-v2.5.0.json", "api-v2.6.0.json", "api-v2.7.0.json", "api-v2.8.0.json"]
        for name in names:
            with self.subTest(contract=name):
                report = check_api_compatibility(ROOT / "compatibility" / name)
                self.assertTrue(report["compatible"], report)

if __name__ == "__main__":
    unittest.main()
