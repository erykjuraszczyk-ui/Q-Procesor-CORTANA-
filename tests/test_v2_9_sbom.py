import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from qwp777_sbom import create_sbom, verify_sbom, SbomError

class V29SbomTests(unittest.TestCase):
    def test_cyclonedx_sbom_generated_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'docs').mkdir(); (root/'VERSION').write_text('3.1.0\n')
            (root/'DEPENDENCIES.json').write_bytes((ROOT/'DEPENDENCIES.json').read_bytes())
            report=create_sbom(root)
            self.assertEqual(report['bomFormat'], 'CycloneDX')
            self.assertEqual(report['specVersion'], '1.6')
            self.assertEqual(report['metadata']['component']['version'], '3.1.0')
            self.assertTrue(verify_sbom(root)['verified'])
    def test_removed_dependency_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'docs').mkdir(); (root/'VERSION').write_text('3.1.0\n')
            (root/'DEPENDENCIES.json').write_bytes((ROOT/'DEPENDENCIES.json').read_bytes())
            create_sbom(root)
            p=root/'docs/SBOM.cdx.json'; obj=json.loads(p.read_text()); obj['components'].pop(); p.write_text(json.dumps(obj))
            result=verify_sbom(root)
            self.assertFalse(result['verified']); self.assertTrue(result['missing_components'])
    def test_policy_change_invalidates_existing_sbom(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'docs').mkdir(); (root/'VERSION').write_text('3.1.0\n')
            (root/'DEPENDENCIES.json').write_bytes((ROOT/'DEPENDENCIES.json').read_bytes())
            create_sbom(root)
            (root/'DEPENDENCIES.json').write_text((root/'DEPENDENCIES.json').read_text()+'\n')
            self.assertFalse(verify_sbom(root)['verified'])
    def test_output_outside_release_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'release'; root.mkdir(); (root/'VERSION').write_text('3.1.0\n')
            (root/'DEPENDENCIES.json').write_bytes((ROOT/'DEPENDENCIES.json').read_bytes())
            with self.assertRaises(SbomError): create_sbom(root, Path(tmp)/'outside.json')
    def test_bad_policy_schema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'docs').mkdir(); (root/'VERSION').write_text('3.1.0\n')
            (root/'DEPENDENCIES.json').write_text('{}')
            with self.assertRaises(SbomError): create_sbom(root)

if __name__=='__main__': unittest.main()
