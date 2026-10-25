import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from qwp777_stabilizer import StabilizerSimulator,StabilizerError
class TestStabilizer(unittest.TestCase):
 def test_777_allocates(self): self.assertEqual(len(StabilizerSimulator(777).x),1554)
 def test_h_random(self):
  seen=set()
  for seed in range(20):
   s=StabilizerSimulator(1,seed); s.h(0); seen.add(s.measure(0))
  self.assertEqual(seen,{0,1})
 def test_x_one(self): self.assertEqual(StabilizerSimulator(1).x_gate(0).measure(0),1)
 def test_zero(self): self.assertEqual(StabilizerSimulator(1).measure(0),0)
 def test_bad_index(self):
  with self.assertRaises(StabilizerError): StabilizerSimulator(2).h(2)
 def test_bad_cx(self):
  with self.assertRaises(StabilizerError): StabilizerSimulator(2).cx(0,0)
 def test_nonclifford_rejected(self):
  with self.assertRaises(StabilizerError): StabilizerSimulator(1).run([{"gate":"T","qubits":[0]}])
 def test_deterministic_entangled_ghz(self):
  s=StabilizerSimulator(3,seed=4); s.h(0).cx(0,1).cx(0,2)
  first=s.measure(0); self.assertEqual(s.measure(1),first); self.assertEqual(s.measure(2),first)
