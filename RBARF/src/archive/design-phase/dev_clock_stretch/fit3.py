"""Model: o[s]=pos[s]*cyc, P=40*cyc. Fit cyc (+ start phase) per capture."""
import sys
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


def err_of(samples, bits, cyc, t0, nloop=None):
    e = 0
    n = 0
    tmax = len(bits) * BIT
    for i, sl, v in samples:
        t = t0 + (i * (nloop or 40) + POS[sl]) * cyc
        if t >= tmax + 1500:
            break
        n += 1
        if ideal(t, bits) != v:
            e += 1
    return e, n


if __name__ == '__main__':
    meta, caps = load_dataset()
    tot = 0
    totn = 0
    for c in caps:
        s = linearize(c['capture'])
        bits = frame_bits(c['frame'])
        best = None
        for ci in range(400):
            cyc = 62.0 + ci * 0.005
            for ti in range(-8, 9):
                t0 = ti * 8.0
                e, n = err_of(s, bits, cyc, t0)
                if best is None or e < best[0]:
                    best = (e, cyc, t0, n)
        e, cyc, t0, n = best
        tot += e
        totn += n
        print(f"{c['pattern']:11s} {c['rep']} err={e:3d}/{n} cyc={cyc:.3f} P={40*cyc:8.2f} t0={t0:6.1f}")
    print("TOTAL", tot, totn, tot / totn)
