"""Phase diagnostics: level vs (t mod 1250) for known bits."""
import sys
from collections import Counter
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
POS = [1, 5, 9, 13, 17, 21, 27, 32]


def frame_bits(hexstr):
    return [int(x) for byte in bytes.fromhex(hexstr) for x in f"{byte:08b}"]


def ideal(t, bits):
    if t < 0:
        return 0
    k = int(t // BIT)
    if k >= len(bits):
        return 0
    return 1 if (t - k * BIT) < (700.0 if bits[k] else 350.0) else 0


def best_fit(s, bits):
    best = None
    for ci in range(500):
        cyc = 62.2 + ci * 0.004
        for ti in range(-10, 11):
            t0 = ti * 6.0
            e = 0
            tmax = len(bits) * BIT
            for i, sl, v in s:
                t = t0 + (i * 40 + POS[sl]) * cyc
                if t >= tmax + 1500:
                    break
                if ideal(t, bits) != v:
                    e += 1
            if best is None or e < best[0]:
                best = (e, cyc, t0)
    return best


if __name__ == '__main__':
    meta, caps = load_dataset()
    pat = sys.argv[1] if len(sys.argv) > 1 else 'ones'
    for c in caps:
        if c['pattern'] == pat and c['rep'] == 0:
            break
    s = linearize(c['capture'])
    bits = frame_bits(c['frame'])
    e, cyc, t0 = best_fit(s, bits)
    print('fit', e, cyc, t0)
    tmax = len(bits) * BIT
    # histogram of level by phase bucket, per bit value, per slot
    buckets = {}
    for i, sl, v in s:
        t = t0 + (i * 40 + POS[sl]) * cyc
        if t >= tmax:
            break
        k = int(t // BIT)
        ph = t - k * BIT
        b = bits[k]
        key = (b, int(ph // 50))
        d = buckets.setdefault(key, Counter())
        d[v] += 1
    for b in (0, 1):
        print('bit', b)
        for bk in range(25):
            d = buckets.get((b, bk))
            if d:
                print(f"  ph {bk*50:5d}-{bk*50+49:5d}  low={d[0]:3d} high={d[1]:3d}")
