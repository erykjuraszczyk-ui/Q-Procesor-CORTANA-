"""Pearson chi-square test for two independent multinomial count samples.

The test is intentionally conservative: it reports an inconclusive status when
any expected table cell is below 5. Its p-value is an approximate asymptotic
test and does not correct for multiple comparisons.
"""
from __future__ import annotations
import math

class SignificanceError(ValueError):
    pass

def _validate_counts(counts, label):
    if not isinstance(counts, dict) or not counts:
        raise SignificanceError(f"{label} counts must be a non-empty dictionary")
    for key, value in counts.items():
        if not isinstance(key, str) or not key or any(bit not in "01" for bit in key):
            raise SignificanceError(f"{label} contains an invalid bitstring")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SignificanceError(f"{label} counts must be non-negative integers")
    widths = {len(key) for key in counts}
    if len(widths) != 1:
        raise SignificanceError(f"{label} bitstrings must have equal widths")
    total = sum(counts.values())
    if total <= 0:
        raise SignificanceError(f"{label} counts must sum to a positive number")
    return total

def _regularized_gamma_q(a, x):
    """Regularized upper incomplete gamma Q(a,x), Numerical Recipes-style."""
    if a <= 0 or x < 0:
        raise ValueError("gamma arguments out of range")
    if x == 0:
        return 1.0
    gln = math.lgamma(a)
    eps = 3.0e-14
    tiny = 1.0e-300
    if x < a + 1.0:
        ap = a
        term = 1.0 / a
        total = term
        for _ in range(10000):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * eps:
                break
        p = total * math.exp(-x + a * math.log(x) - gln)
        return min(1.0, max(0.0, 1.0 - p))
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / max(abs(b), tiny)
    if b < 0:
        d = -d
    h = d
    for i in range(1, 10000):
        an = -float(i) * (float(i) - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    q = math.exp(-x + a * math.log(x) - gln) * h
    return min(1.0, max(0.0, q))

def chi_square_two_sample_test(left_counts, right_counts, alpha=0.05):
    """Test whether two independent empirical categorical distributions differ."""
    for label, value in (("alpha", alpha),):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 < value < 1.0:
            raise SignificanceError(f"{label} must be a number strictly between 0 and 1")
    n_left = _validate_counts(left_counts, "left")
    n_right = _validate_counts(right_counts, "right")
    if {len(k) for k in left_counts} != {len(k) for k in right_counts}:
        raise SignificanceError("left and right outcome widths do not match")
    outcomes = sorted(k for k in (set(left_counts) | set(right_counts))
                      if left_counts.get(k, 0) + right_counts.get(k, 0) > 0)
    df = len(outcomes) - 1
    base = {
        "method": "Pearson chi-square test of homogeneity",
        "alpha": float(alpha),
        "left_shots": n_left,
        "right_shots": n_right,
        "categories": len(outcomes),
        "degrees_of_freedom": max(0, df),
        "p_value": None,
        "statistically_significant": None,
        "status": "inconclusive",
    }
    if df < 1:
        base["reason"] = "At least two non-empty outcome categories are required."
        return base
    grand = n_left + n_right
    chi2 = 0.0
    expected_values = []
    for outcome in outcomes:
        pooled = left_counts.get(outcome, 0) + right_counts.get(outcome, 0)
        exp_left = n_left * pooled / grand
        exp_right = n_right * pooled / grand
        expected_values.extend((exp_left, exp_right))
        chi2 += (left_counts.get(outcome, 0) - exp_left) ** 2 / exp_left
        chi2 += (right_counts.get(outcome, 0) - exp_right) ** 2 / exp_right
    base["chi_square_statistic"] = chi2
    base["minimum_expected_cell_count"] = min(expected_values)
    if min(expected_values) < 5.0:
        base["reason"] = "At least one expected cell count is below 5; the asymptotic chi-square approximation was not applied."
        base["notes"] = ["Collect more shots or use a suitable exact/permutation test for sparse tables."]
        return base
    p_value = _regularized_gamma_q(df / 2.0, chi2 / 2.0)
    base["p_value"] = p_value
    base["statistically_significant"] = bool(p_value < alpha)
    base["status"] = "difference_detected" if p_value < alpha else "no_significant_difference_detected"
    base["reason"] = (
        "The p-value is below alpha." if p_value < alpha
        else "The p-value is not below alpha; this is not proof that the distributions are equivalent."
    )
    base["notes"] = [
        "The test assumes independent samples and uses an asymptotic approximation.",
        "This p-value is not adjusted for multiple comparisons.",
        "A detected difference does not identify its cause or prove either backend is correct."
    ]
    return base
