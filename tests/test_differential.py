import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from qwp777_stabilizer import StabilizerSimulator
from qwp777_differential import run_statevector

class TestDifferentialOracle(unittest.TestCase):
    def test_deterministic_x_measure_matches_oracle(self):
        gates=[{"gate":"X","qubits":[0]},{"gate":"MEASURE","qubits":[0]}]
        got=StabilizerSimulator(1,seed=5).run(gates).measurements
        expected,_=run_statevector(1,gates,seed=5)
        self.assertEqual(got,expected)
    def test_deterministic_bell_z_correlations(self):
        prefix=[{"gate":"H","qubits":[0]},{"gate":"CX","qubits":[0,1]}]
        for seed in range(30):
            g1=prefix+[{"gate":"MEASURE","qubits":[0]}]
            a=StabilizerSimulator(2,seed).run(g1).measurements[0]
            g2=prefix+[{"gate":"MEASURE","qubits":[0]},{"gate":"MEASURE","qubits":[1]}]
            b=StabilizerSimulator(2,seed).run(g2).measurements
            self.assertEqual(b[0],b[1])
            self.assertIn(a,(0,1))
    def test_oracle_caps_size(self):
        with self.assertRaises(ValueError): run_statevector(13,[])
