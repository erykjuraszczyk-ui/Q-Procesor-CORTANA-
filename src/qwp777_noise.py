"""Explicitly synthetic measurement bit-flip noise for prototype experiments."""
from __future__ import annotations
import random
from collections import Counter

class NoiseModelError(ValueError):
    pass

def apply_bit_flip_noise(counts, probability, seed=7):
    """Apply independent synthetic bit flips to sampled bitstring counts.

    This is post-processing noise, not a calibrated physical-device model.
    """
    if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not 0.0 <= probability <= 1.0:
        raise NoiseModelError("probability must be a number in [0, 1]")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1:
        raise NoiseModelError("seed must be an integer in 0..4294967295")
    if not isinstance(counts, dict) or not counts:
        raise NoiseModelError("counts must be a non-empty dictionary")
    for bitstring, count in counts.items():
        if not isinstance(bitstring, str) or not bitstring or any(bit not in "01" for bit in bitstring):
            raise NoiseModelError("outcome keys must be non-empty bitstrings")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise NoiseModelError("counts must be non-negative integers")
    rng = random.Random(seed)
    out = Counter()
    for bits, count in sorted(counts.items()):
        for _ in range(count):
            changed = list(bits)
            for i, bit in enumerate(changed):
                if rng.random() < probability:
                    changed[i] = "1" if bit == "0" else "0"
            out["".join(changed)] += 1
    return dict(sorted(out.items()))
