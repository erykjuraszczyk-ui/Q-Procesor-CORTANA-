import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from qwp777_sbom import create_sbom
from qwp777_dependency_audit import audit_dependencies, DependencyAuditError

class V29DependencyAuditTests(unittest.TestCase):
    def _root(self, tmp):
        root=Path(tmp)/'release'; (root/'src').mkdir(parents=True); (root/'docs').mkdir()
        (root/'VERSION').write_text('3.1.0\n')
        shutil.copy(ROOT/'DEPENDENCIES.json', root/'DEPENDENCIES.json')
        shutil.copy(ROOT/'src/qwp777_ed25519.py', root/'src/qwp777_ed25519.py')
        shutil.copy(ROOT/'src/qwp777_qiskit_adapter.py', root/'src/qwp777_qiskit_adapter.py')
        create_sbom(root)
        return root
    def test_declared_optional_imports_are_covered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); report=audit_dependencies(root)
            self.assertTrue(report['summary']['passed'], report['summary'])
            self.assertEqual(report['summary']['undeclared_imports'], [])
    def test_undeclared_external_import_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); (root/'src/plugin.py').write_text('import not_a_declared_library\n')
            report=audit_dependencies(root)
            self.assertFalse(report['summary']['passed'])
            self.assertIn('not_a_declared_library', report['summary']['undeclared_imports'])
    def test_no_live_vulnerability_scan_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); report=audit_dependencies(root)
            security=report['security_assessment']
            self.assertFalse(security['live_vulnerability_database_used'])
            self.assertFalse(security['vulnerability_scan_performed'])
            self.assertEqual(security['vulnerability_status'], 'not_assessed')
    def test_sbom_missing_dependency_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); p=root/'docs/SBOM.cdx.json'; obj=json.loads(p.read_text())
            obj['components'].pop(); p.write_text(json.dumps(obj))
            report=audit_dependencies(root)
            self.assertFalse(report['summary']['passed'])
            self.assertFalse(report['summary']['sbom_verified'])
    def test_policy_schema_invalid_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self._root(tmp); (root/'DEPENDENCIES.json').write_text('{}')
            with self.assertRaises(DependencyAuditError): audit_dependencies(root)

if __name__=='__main__': unittest.main()
