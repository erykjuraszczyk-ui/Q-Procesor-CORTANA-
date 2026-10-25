class CircuitSchemaError(ValueError): pass
SINGLE={"H","S","X","Z","MEASURE"}; DOUBLE={"CX","CZ"}
def validate_gates(gates,num_qubits):
 if isinstance(num_qubits,bool) or not isinstance(num_qubits,int) or not 1<=num_qubits<=777: raise CircuitSchemaError("num_qubits must be in 1..777")
 if not isinstance(gates,list): raise CircuitSchemaError("gates must be a list")
 for i,item in enumerate(gates):
  if not isinstance(item,dict): raise CircuitSchemaError(f"gate {i} must be an object")
  gate=item.get("gate")
  if not isinstance(gate,str) or gate.upper() not in SINGLE|DOUBLE: raise CircuitSchemaError(f"gate {i} unsupported")
  qs=item.get("qubits"); arity=2 if gate.upper() in DOUBLE else 1
  if not isinstance(qs,list) or len(qs)!=arity: raise CircuitSchemaError(f"gate {i} expects {arity} qubits")
  for q in qs:
   if isinstance(q,bool) or not isinstance(q,int) or not 0<=q<num_qubits: raise CircuitSchemaError(f"gate {i} index out of range")
  if arity==2 and qs[0]==qs[1]: raise CircuitSchemaError(f"gate {i} operands must differ")
 return True
