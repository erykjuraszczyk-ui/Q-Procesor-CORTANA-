import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from qwp777_validation import validate_gates,CircuitSchemaError
class TestValidation(unittest.TestCase):
 def test_valid(self): self.assertTrue(validate_gates([{"gate":"H","qubits":[0]}],1))
 def test_unknown(self):
  with self.assertRaises(CircuitSchemaError): validate_gates([{"gate":"T","qubits":[0]}],1)
 def test_index(self):
  with self.assertRaises(CircuitSchemaError): validate_gates([{"gate":"H","qubits":[1]}],1)
 def test_arity(self):
  with self.assertRaises(CircuitSchemaError): validate_gates([{"gate":"CX","qubits":[0]}],2)
