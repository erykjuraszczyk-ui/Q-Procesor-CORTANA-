"""Confidence intervals for sampled outcome proportions.

Intervals quantify sampling uncertainty under an approximate binomial model.
They do not account for systematic simulator bugs, circuit mismatch, or device drift.
"""
from __future__ import annotations
import math

class ConfidenceError(ValueError):
    pass

_Z_CRITICAL = {
    0.80: 1.2815515655446004,
    0.90: 1.6448536269514722,
    0.95: 1.959963984540054,
    0.98: 2.3263478740408408,
    0.99: 2.5758293035489004,
}

def z_critical(confidence_level):
    if isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float)):
        raise ConfidenceError("confidence_level must be a number")
    level = float(confidence_level)
    if level not in _Z_CRITICAL:
        raise ConfidenceError("supported confidence levels: 0.80, 0.90, 0.95, 0.98, 0.99")
    return _Z_CRITICAL[level]

def wilson_interval(successes, trials, confidence_level=0.95):
    """Return Wilson score interval [lower, upper] for a binomial proportion."""
    if isinstance(trials, bool) or not isinstance(trials, int) or trials <= 0:
        raise ConfidenceError("trials must be a positive integer")
    if isinstance(successes, bool) or not isinstance(successes, int) or not 0 <= successes <= trials:
        raise ConfidenceError("successes must be an integer in 0..trials")
    z = z_critical(confidence_level)
    p = successes / trials
    z2 = z * z
    denom = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / denom
    half = z * math.sqrt((p * (1-p) / trials) + (z2 / (4 * trials * trials))) / denom
    return [max(0.0, center-half), min(1.0, center+half)]

def compare_proportion_intervals(left_counts, right_counts, confidence_level=0.95):
    """Compute Wilson intervals and approximate CI for right-minus-left probability."""
    if not isinstance(left_counts, dict) or not isinstance(right_counts, dict):
        raise ConfidenceError("counts inputs must be dictionaries")
    def total_of(counts, label):
        if not counts:
            raise ConfidenceError(f"{label} counts must not be empty")
        for k, v in counts.items():
            if not isinstance(k, str) or not k or any(c not in "01" for c in k):
                raise ConfidenceError(f"{label} has invalid outcome key")
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ConfidenceError(f"{label} counts must be non-negative integers")
        total = sum(counts.values())
        if total <= 0:
            raise ConfidenceError(f"{label} counts must sum to a positive number")
        if len({len(k) for k in counts}) != 1:
            raise ConfidenceError(f"{label} outcome bitstrings must have equal widths")
        return total
    n1, n2 = total_of(left_counts, "left"), total_of(right_counts, "right")
    if {len(k) for k in left_counts} != {len(k) for k in right_counts}:
        raise ConfidenceError("left and right outcome widths do not match")
    z = z_critical(confidence_level)
    outcomes = sorted(set(left_counts) | set(right_counts))
    result = {}
    for key in outcomes:
        x1, x2 = left_counts.get(key, 0), right_counts.get(key, 0)
        p1, p2 = x1/n1, x2/n2
        se = math.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
        delta = p2-p1
        result[key] = {
            "left_probability": p1,
            "left_wilson_interval": wilson_interval(x1, n1, confidence_level),
            "right_probability": p2,
            "right_wilson_interval": wilson_interval(x2, n2, confidence_level),
            "delta_right_minus_left": delta,
            "approx_delta_interval": [max(-1.0, delta-z*se), min(1.0, delta+z*se)]
        }
    return {
        "confidence_level": float(confidence_level),
        "method": "Wilson score intervals; normal-approximation interval for independent proportion difference",
        "left_shots": n1, "right_shots": n2, "outcomes": result,
        "notes": ["Intervals describe sampling uncertainty, not systematic error.",
                  "Outcome-wise intervals are not simultaneous family-wise confidence intervals."]
    }
