"""QWP-777 v0.8: phase-aware stabilizer tableau prototype.

Supports H, S, X, Z, CX, CZ and computational-basis measurements.
Educational implementation; use differential tests before research use.
"""
from __future__ import annotations
import random
from dataclasses import dataclass

class StabilizerError(ValueError): pass

@dataclass
class StabilizerResult:
    num_qubits: int
    measurements: dict[int,int]
    final_tableau: list[list[int]]

class StabilizerSimulator:
    def __init__(self, num_qubits:int, seed:int=7):
        if isinstance(num_qubits,bool) or not isinstance(num_qubits,int) or not 1<=num_qubits<=777:
            raise StabilizerError("num_qubits must be an integer in 1..777")
        if isinstance(seed,bool) or not isinstance(seed,int) or not 0<=seed<=2**32-1:
            raise StabilizerError("seed must be an integer in 0..4294967295")
        self.n=num_qubits; self.rng=random.Random(seed)
        self.x=[[0]*self.n for _ in range(2*self.n)]
        self.z=[[0]*self.n for _ in range(2*self.n)]
        self.r=[0]*(2*self.n)
        for q in range(self.n):
            self.x[q][q]=1
            self.z[self.n+q][q]=1
    def _check(self,q):
        if isinstance(q,bool) or not isinstance(q,int) or not 0<=q<self.n:
            raise StabilizerError(f"qubit index must be in 0..{self.n-1}")
    def h(self,q):
        self._check(q)
        for i in range(2*self.n):
            if self.x[i][q] and self.z[i][q]: self.r[i]^=1
            self.x[i][q],self.z[i][q]=self.z[i][q],self.x[i][q]
        return self
    def s(self,q):
        self._check(q)
        for i in range(2*self.n):
            if self.x[i][q] and self.z[i][q]: self.r[i]^=1
            self.z[i][q]^=self.x[i][q]
        return self
    def x_gate(self,q):
        self._check(q)
        for i in range(2*self.n):
            if self.z[i][q]: self.r[i]^=1
        return self
    def z_gate(self,q):
        self._check(q)
        for i in range(2*self.n):
            if self.x[i][q]: self.r[i]^=1
        return self
    def cx(self,c,t):
        self._check(c); self._check(t)
        if c==t: raise StabilizerError("CX control and target must differ")
        for i in range(2*self.n):
            if self.x[i][c] and self.z[i][t] and (self.x[i][t]^self.z[i][c]^1): self.r[i]^=1
            self.x[i][t]^=self.x[i][c]; self.z[i][c]^=self.z[i][t]
        return self
    def cz(self,a,b):
        self._check(a); self._check(b)
        if a==b: raise StabilizerError("CZ operands must differ")
        return self.h(b).cx(a,b).h(b)
    def _rowsum(self,h,i):
        def g(x1,z1,x2,z2):
            return (x1*z1*(x2^z2)+z1*x2*(x2^z2))%2
        phase=2*self.r[h]+2*self.r[i]
        for q in range(self.n): phase+=2*g(self.x[h][q],self.z[h][q],self.x[i][q],self.z[i][q])
        self.r[h]=(phase//2)%2
        for q in range(self.n):
            self.x[h][q]^=self.x[i][q]; self.z[h][q]^=self.z[i][q]
    def measure(self,q):
        self._check(q)
        pivot=next((i for i in range(self.n,2*self.n) if self.x[i][q]),None)
        if pivot is not None:
            for i in range(2*self.n):
                if i!=pivot and self.x[i][q]: self._rowsum(i,pivot)
            self.x[pivot-self.n]=self.x[pivot].copy()
            self.z[pivot-self.n]=self.z[pivot].copy()
            self.r[pivot-self.n]=self.r[pivot]
            self.x[pivot]=[0]*self.n; self.z[pivot]=[0]*self.n; self.z[pivot][q]=1
            self.r[pivot]=self.rng.randrange(2)
            return self.r[pivot]
        sx=[0]*self.n; sz=[0]*self.n; sr=0
        def add(row):
            nonlocal sr
            def g(x1,z1,x2,z2):
                return (x1*z1*(x2^z2)+z1*x2*(x2^z2))%2
            phase=2*sr+2*self.r[row]
            for j in range(self.n): phase+=2*g(sx[j],sz[j],self.x[row][j],self.z[row][j])
            sr=(phase//2)%2
            for j in range(self.n):
                sx[j]^=self.x[row][j]; sz[j]^=self.z[row][j]
        for i in range(self.n):
            if self.x[i][q]: add(i+self.n)
        if any(sx) or sz[q]!=1 or any(v for j,v in enumerate(sz) if j!=q):
            raise StabilizerError("deterministic measurement tableau invariant failed")
        return sr
    def run(self,gates, include_tableau=True):
        """Execute gates. Set include_tableau=False to avoid copying the final tableau.

        The default preserves historical behavior for callers that inspect final_tableau.
        """
        if not isinstance(include_tableau, bool):
            raise StabilizerError("include_tableau must be a boolean")
        measurements={}
        for item in gates:
            gate=item["gate"].upper(); qs=item.get("qubits",[])
            if gate=="H": self.h(qs[0])
            elif gate=="S": self.s(qs[0])
            elif gate=="X": self.x_gate(qs[0])
            elif gate=="Z": self.z_gate(qs[0])
            elif gate=="CX": self.cx(qs[0],qs[1])
            elif gate=="CZ": self.cz(qs[0],qs[1])
            elif gate=="MEASURE": measurements[qs[0]]=self.measure(qs[0])
            else: raise StabilizerError(f"unsupported Clifford gate: {gate}")
        final_tableau = ([self.x[i]+self.z[i]+[self.r[i]] for i in range(2*self.n)]
                         if include_tableau else [])
        return StabilizerResult(self.n, measurements, final_tableau)
