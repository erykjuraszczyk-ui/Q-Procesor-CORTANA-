import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

class V31PipelineTests(unittest.TestCase):
    def test_release_metadata_and_contract_exist(self):
        self.assertEqual((ROOT / "VERSION").read_text().strip(), "3.1.0")
        self.assertTrue((ROOT / "compatibility/api-v3.1.0.json").is_file())
        self.assertTrue((ROOT / "regression/baselines/v3.1.0.json").is_file())

    def test_github_actions_builds_and_publishes_only_matching_tags(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        workflow += (ROOT / "scripts/ci_release.sh").read_text()
        for gate in ("compileall", "unittest discover", "qwp777_api_compat.py",
                     "qwp777_regression.py", "qwp777_sbom.py", "qwp777_dependency_audit.py",
                     "qwp777_release_audit.py", "qwp777_release_package.py",
                     "actions/upload-artifact@v4", "actions/attest@v4",
                     "softprops/action-gh-release@v3", "check_release_tag.py",
                     "refs/tags/v", "contents: write", "id-token: write",
                     "attestations: write", "artifact-metadata: write"):
            self.assertIn(gate, workflow)
        self.assertIn("permissions:", (ROOT / ".github/workflows/release.yml").read_text())
        self.assertIn("Qwantum-Processor-777-v${VERSION}.zip", (ROOT / "scripts/ci_release.sh").read_text())

    def test_pipeline_documents_signing_trust_boundary(self):
        doc = (ROOT / "docs/CI_RELEASE_PIPELINE.md").read_text().lower()
        self.assertIn("private key", doc)
        self.assertIn("offline", doc)
        self.assertIn("not been executed", doc)

    def test_local_pipeline_is_fail_fast_and_does_not_embed_private_key(self):
        script = (ROOT / "scripts/ci_release.sh").read_text()
        self.assertIn("set -euo pipefail", script)
        self.assertIn("qwp777_release_package.py build", script)
        self.assertNotIn("BEGIN PRIVATE KEY", script)

if __name__ == "__main__":
    unittest.main()
