import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qwp777_release_package import (
    ReleasePackageError, create_manifest, verify_manifest, build_archive, verify_archive,
)


class ReleasePackageTests(unittest.TestCase):
    def make_root(self, base):
        root = Path(base) / "release"
        (root / "src").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "VERSION").write_text("3.1.0\n", encoding="utf-8")
        (root / "src" / "app.py").write_text("print('qwp')\n", encoding="utf-8")
        (root / "docs" / "notes.md").write_text("release notes\n", encoding="utf-8")
        return root

    def test_manifest_created_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            payload = create_manifest(root)
            self.assertEqual(payload["manifest_schema"], "qwp777-release-manifest-1")
            self.assertEqual(payload["software"]["release"], "3.1.0")
            self.assertFalse(payload["self_hashing"])
            report = verify_manifest(root)
            self.assertTrue(report["verified"], report)
            self.assertEqual(report["files_expected"], 3)

    def test_modified_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            create_manifest(root)
            (root / "src" / "app.py").write_text("tampered\n", encoding="utf-8")
            report = verify_manifest(root)
            self.assertFalse(report["verified"])
            self.assertIn("src/app.py", report["hash_or_size_mismatches"])

    def test_missing_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            create_manifest(root)
            (root / "docs" / "notes.md").unlink()
            self.assertFalse(verify_manifest(root)["verified"])

    def test_unexpected_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            create_manifest(root)
            (root / "unexpected.txt").write_text("extra", encoding="utf-8")
            report = verify_manifest(root)
            self.assertFalse(report["verified"])
            self.assertEqual(report["unexpected_files"], ["unexpected.txt"])

    def test_manifest_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            payload = create_manifest(root)
            payload["files"].append({"path": "../outside", "size_bytes": 0, "sha256": "x"})
            (root / "docs" / "RELEASE_MANIFEST.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ReleasePackageError):
                verify_manifest(root)

    def test_manifest_rejects_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            payload = create_manifest(root)
            payload["files"].append(payload["files"][0])
            (root / "docs" / "RELEASE_MANIFEST.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ReleasePackageError):
                verify_manifest(root)

    def test_builds_zip_and_detached_sha256_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            archive = Path(tmp) / "QWP-777-v3.1.0.zip"
            result = build_archive(root, archive)
            self.assertTrue(result["manifest_verified"])
            self.assertEqual(result["zip_integrity"], "passed")
            checked = verify_archive(archive)
            self.assertTrue(checked["verified"], checked)
            with zipfile.ZipFile(archive) as zf:
                self.assertIsNone(zf.testzip())
                self.assertIn("release/docs/RELEASE_MANIFEST.json", zf.namelist())

    def test_archive_sidecar_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            archive = Path(tmp) / "QWP-777-v3.1.0.zip"
            build_archive(root, archive)
            archive.write_bytes(archive.read_bytes() + b"tamper")
            self.assertFalse(verify_archive(archive)["verified"])

    def test_rejects_version_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            (root / "VERSION").write_text("9.9.9\n", encoding="utf-8")
            with self.assertRaises(ReleasePackageError):
                create_manifest(root)


if __name__ == "__main__":
    unittest.main()
