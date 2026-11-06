"""Joint fit of P and slot offsets per capture (dev only, uses full frame)."""
import sys
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


def cost(samples, bits, P, o, tmax):
    err = 0
    n = 0
    for i, sl, v in samples:
        t = i * P + o[sl]
        if t >= tmax + 2000:
            break
        n += 1
        if ideal_level(t, bits) != v:
            err += 1
    return err


def fit(samples, bits):
    tmax = len(bits) * BIT
    o = [p * 2507.3 / 37.0 for p in [1, 5, 9, 13, 17, 21, 27, 32]]
    P = 2507.3
    best = cost(samples, bits, P, o, tmax)
    step_p = 8.0
    step_o = 60.0
    for it in range(200):
        improved = False
        for dp in (step_p, -step_p):
            e = cost(samples, bits, P + dp, o, tmax)
            if e < best:
                best, P = e, P + dp
                improved = True
        for k in range(8):
            for do in (step_o, -step_o):
                o2 = list(o)
                o2[k] += do
                e = cost(samples, bits, P, o2, tmax)
                if e < best:
                    best, o = e, o2
                    improved = True
        if not improved:
            step_p *= 0.5
            step_o *= 0.5
            if step_o < 0.4:
                break
    return best, P, o


if __name__ == '__main__':
    meta, caps = load_dataset()
    for c in caps:
        s = linearize(c['capture'])
        bits = frame_bits(c['frame'])
        e, P, o = fit(s, bits)
        print(f"{c['pattern']:11s} {c['rep']} err={e:4d} P={P:8.2f} o=" +
              " ".join(f"{x:7.1f}" for x in o))
