"""Fit timing model: t(i,slot) = i*P + o[slot], using known header+trailer bits."""
import sys, json
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
T0H = 350.0
T1H = 700.0


def frame_bits(hexstr):
    b = bytes.fromhex(hexstr)
    return [int(x) for byte in b for x in f"{byte:08b}"]


def ideal_level(t, bits):
    if t < 0:
        return 0
    k = int(t // BIT)
    if k >= len(bits):
        return 0
    ph = t - k * BIT
    return 1 if ph < (T1H if bits[k] else T0H) else 0


def cost(samples, bits, P, o, mask_range):
    err = 0
    n = 0
    for i, sl, v in samples:
        t = i * P + o[sl]
        if not (mask_range[0] <= t < mask_range[1]):
            continue
        n += 1
        if ideal_level(t, bits) != v:
            err += 1
    return err, n


def fit_one(samples, bits, nbits_frame):
    total = nbits_frame * BIT
    # regions with known bits: header (0..40000) and trailer (last 32 bits)
    best = None
    # coarse grid over P
    o0 = [p * 2507.3 / 37.0 for p in [1, 5, 9, 13, 17, 21, 27, 32]]
    for P in [2495 + 0.5 * k for k in range(80)]:
        e, n = cost(samples, bits, P, o0, (0, total))
        if best is None or e < best[0]:
            best = (e, P)
    return best


if __name__ == '__main__':
    meta, caps = load_dataset()
    for c in caps[:6]:
        s = linearize(c['capture'])
        bits = frame_bits(c['frame'])
        print(c['pattern'], c['rep'], fit_one(s, bits, len(bits)))
