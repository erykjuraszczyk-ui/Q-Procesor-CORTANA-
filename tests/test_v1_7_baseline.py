import hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_baseline import refresh_baseline, BaselineRefreshError
from qwp777_regression import run_regression_suite

class V17BaselineTests(unittest.TestCase):
    def test_explicit_approval_required(self):
        source = Path(__file__).resolve().parents[1] / "regression" / "baselines" / "v1.5.0.json"
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "v1.7.0.json"
            with self.assertRaises(BaselineRefreshError):
                refresh_baseline(source, target, "1.7.0", approved=False)
            self.assertFalse(target.exists())

    def test_refresh_writes_new_versioned_baseline(self):
        source = Path(__file__).resolve().parents[1] / "regression" / "baselines" / "v1.5.0.json"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "v1.7.0.json"
            report = refresh_baseline(source, target, "1.7.0", approved=True)
            self.assertTrue(target.exists())
            self.assertEqual(source.read_bytes(), original)
            payload = json.loads(target.read_text())
            self.assertEqual(payload["baseline_release"], "1.7.0")
            self.assertEqual(payload["parent_baseline"]["baseline_release"], "1.5.0")
            sidecar = Path(str(target)+".sha256").read_text().split()[0]
            self.assertEqual(sidecar, hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual(report["cases_written"], 6)
            self.assertTrue(run_regression_suite(target)["summary"]["passed"])

    def test_existing_baseline_not_overwritten(self):
        source = Path(__file__).resolve().parents[1] / "regression" / "baselines" / "v1.5.0.json"
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "existing.json"
            target.write_text('{"keep": true}')
            with self.assertRaises(BaselineRefreshError):
                refresh_baseline(source, target, "1.7.0", approved=True)
            self.assertEqual(json.loads(target.read_text()), {"keep": True})

    def test_semver_required(self):
        source = Path(__file__).resolve().parents[1] / "regression" / "baselines" / "v1.5.0.json"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(BaselineRefreshError):
                refresh_baseline(source, Path(temp)/"base.json", "../oops", approved=True)

if __name__ == "__main__":
    unittest.main()
