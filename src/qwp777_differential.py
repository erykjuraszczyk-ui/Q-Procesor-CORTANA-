"""Small exact statevector oracle used for differential tests of Clifford circuits."""
from __future__ import annotations
import math, random
class OracleError(ValueError): pass

def run_statevector(num_qubits, gates, seed=7):
    if isinstance(num_qubits,bool) or not isinstance(num_qubits,int) or not 1<=num_qubits<=12:
        raise OracleError("oracle supports 1..12 qubits")
    n=num_qubits; size=1<<n
    state=[0j]*size; state[0]=1+0j; rng=random.Random(seed); measured={}
    inv=1/math.sqrt(2)
    for item in gates:
        gate=item["gate"].upper(); qs=item.get("qubits",[])
        if gate=="H":
            q=qs[0]; mask=1<<q
            for i in range(size):
                if not i&mask:
                    a,b=state[i],state[i|mask]
                    state[i]=(a+b)*inv; state[i|mask]=(a-b)*inv
        elif gate in ("X","Z","S"):
            q=qs[0]; mask=1<<q
            for i in range(size):
                if i&mask:
                    if gate=="X": continue
                    if gate=="Z": state[i]=-state[i]
                    else: state[i]*=1j
            if gate=="X":
                for i in range(size):
                    if not i&mask: state[i],state[i|mask]=state[i|mask],state[i]
        elif gate=="CX":
            c,t=qs; cm,tm=1<<c,1<<t
            for i in range(size):
                if i&cm and not i&tm: state[i],state[i|tm]=state[i|tm],state[i]
        elif gate=="CZ":
            a,b=qs; am,bm=1<<a,1<<b
            for i in range(size):
                if i&am and i&bm: state[i]=-state[i]
        elif gate=="MEASURE":
            q=qs[0]; mask=1<<q
            p1=sum(abs(state[i])**2 for i in range(size) if i&mask)
            outcome=1 if rng.random()<p1 else 0
            norm=math.sqrt(p1 if outcome else max(0,1-p1))
            for i in range(size):
                if bool(i&mask)!=bool(outcome): state[i]=0j
                elif norm: state[i]/=norm
            measured[q]=outcome
        else: raise OracleError(f"unsupported gate {gate}")
    return measured, state
