import hashlib, json, sys, tempfile, unittest, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_archive import create_report_archive, ArchiveError

class V16ArchiveTests(unittest.TestCase):
    def test_archives_report_config_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            report = folder / "report.json"
            config = folder / "config.json"
            report_bytes = b'{"report_schema":"demo"}\n'
            config_bytes = b'{"num_qubits":1,"gates":[{"gate":"MEASURE","qubits":[0]}]}\n'
            report.write_bytes(report_bytes)
            config.write_bytes(config_bytes)
            result = create_report_archive(report, config, folder/"archive", "case-a")
            self.assertEqual(result["zip_integrity"], "ok")
            self.assertEqual(result["manifest"]["files"]["report.json"]["sha256"], hashlib.sha256(report_bytes).hexdigest())
            self.assertEqual(result["manifest"]["files"]["configuration.json"]["sha256"], hashlib.sha256(config_bytes).hexdigest())
            with zipfile.ZipFile(result["zip_path"]) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read("case-a/report.json"), report_bytes)
                self.assertEqual(archive.read("case-a/configuration.json"), config_bytes)

    def test_archive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            report = folder/"report.json"; config=folder/"config.json"
            report.write_text('{"ok":true}')
            config.write_text('{"config":true}')
            create_report_archive(report, config, folder/"archive", "same-name")
            with self.assertRaises(ArchiveError):
                create_report_archive(report, config, folder/"archive", "same-name")

    def test_invalid_archive_name_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            report = folder/"report.json"; config=folder/"config.json"
            report.write_text('{"ok":true}')
            config.write_text('{"config":true}')
            with self.assertRaises(ArchiveError):
                create_report_archive(report, config, folder/"archive", "../escape")

if __name__ == "__main__":
    unittest.main()
