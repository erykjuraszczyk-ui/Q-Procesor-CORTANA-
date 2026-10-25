import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_tag.py"

class ReleaseTagGuardTests(unittest.TestCase):
    def run_check(self, tag, version="3.1.0"):
        with tempfile.TemporaryDirectory() as tmp:
            version_file = Path(tmp) / "VERSION"
            version_file.write_text(version + "\n", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--tag", tag, "--version-file", str(version_file)],
                capture_output=True, text=True, check=False
            )

    def test_exact_release_tag_is_accepted(self):
        result = self.run_check("v3.1.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("matches VERSION", result.stdout)

    def test_wrong_patch_or_prefix_is_rejected(self):
        for tag in ("3.1.0", "v3.1.1", "v3.1.0-rc1", "v03.1.0"):
            with self.subTest(tag=tag):
                self.assertNotEqual(self.run_check(tag).returncode, 0)

    def test_non_semver_version_is_rejected(self):
        self.assertNotEqual(self.run_check("v3.1.0", version="3.1").returncode, 0)

if __name__ == "__main__":
    unittest.main()
