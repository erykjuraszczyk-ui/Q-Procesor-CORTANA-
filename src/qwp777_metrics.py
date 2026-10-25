"""Statistical comparison metrics for measurement distributions."""
from __future__ import annotations
import math

class MetricsError(ValueError):
    pass

def _normalize(dist):
    if not isinstance(dist, dict) or not dist:
        raise MetricsError("distribution must be a non-empty mapping")
    vals = {}
    for key, value in dist.items():
        if not isinstance(key, str):
            raise MetricsError("outcome keys must be strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise MetricsError("weights must be finite, non-negative numbers")
        vals[key] = float(value)
    total = sum(vals.values())
    if total <= 0:
        raise MetricsError("distribution total must be positive")
    return {k: v/total for k, v in vals.items()}

def total_variation_distance(p, q):
    """Return TVD = 0.5 * sum_x |p(x)-q(x)|, in [0, 1]."""
    p, q = _normalize(p), _normalize(q)
    return 0.5 * sum(abs(p.get(k, 0.0)-q.get(k, 0.0)) for k in p.keys() | q.keys())

def hellinger_distance(p, q):
    """Return Hellinger distance with the convention H = sqrt(0.5*sum(...)), in [0, 1]."""
    p, q = _normalize(p), _normalize(q)
    return math.sqrt(0.5 * sum((math.sqrt(p.get(k, 0.0))-math.sqrt(q.get(k, 0.0)))**2 for k in p.keys() | q.keys()))
