"""Descriptive statistics for repeated-shot measurement counts."""
from __future__ import annotations
import math

class StatisticsError(ValueError):
    pass

def summarize_counts(counts, shots=None):
    """Return total, observed outcomes, empirical probabilities, and Shannon entropy.

    Entropy is in bits and computed from the empirical distribution. This is a
    descriptive statistic, not a claim about physical hardware entropy.
    """
    if not isinstance(counts, dict) or not counts:
        raise StatisticsError("counts must be a non-empty mapping")
    total = 0
    for outcome, count in counts.items():
        if not isinstance(outcome, str) or not outcome or any(bit not in "01" for bit in outcome):
            raise StatisticsError("outcome keys must be non-empty bit strings")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise StatisticsError("counts must be non-negative integers")
        total += count
    if total <= 0:
        raise StatisticsError("total count must be positive")
    if shots is not None and (isinstance(shots, bool) or not isinstance(shots, int) or shots != total):
        raise StatisticsError("shots must equal the sum of counts")
    probs = {k: v / total for k, v in counts.items() if v > 0}
    entropy = -sum(p * math.log2(p) for p in probs.values())
    return {
        "shots": total,
        "observed_outcomes": len(probs),
        "probabilities": probs,
        "shannon_entropy_bits": entropy
    }
