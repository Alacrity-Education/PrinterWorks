"""Independent measurement of intra-loop slot geometry.

t(i, slot) = u_i + d_slot   (u_i free per iteration, d global, d_0 = 0)
The transmitted waveform is exactly known (dev only), so every sample's
level constrains its time.  Alternately optimise u and d to minimise
level violations.  Also reports the per-iteration loop period u_{i+1}-u_i.
"""
import sys, json
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
T0H = 350.0
T1H = 700.0


def level_at(t, bits):
    if t < 0:
        return 0
    k = int(t // BIT)
    if k >= len(bits):
        return 0
    return 1 if (t - k * BIT) < (T1H if bits[k] else T0H) else 0


def fit(samples, bits, d, u0_guess, niter=8):
    by_it = {}
    for it, sl, v in samples:
        by_it.setdefault(it, []).append((sl, v))
    its = sorted(by_it)
    u = dict(u0_guess)
    for _ in range(niter):
        # optimise u_i
        for i in its:
            base = u[i]
            best = None
            for step in (40.0, 10.0, 2.5):
                lo = best[1] if best else base
                for j in range(-10, 11):
                    cand = lo + j * step
                    e = 0
                    for sl, v in by_it[i]:
                        if level_at(cand + d[sl], bits) != v:
                            e += 1
                    key = (e, abs(cand - base))
                    if best is None or key < (best[0], abs(best[1] - base)):
                        best = (e, cand)
            u[i] = best[1]
        # optimise d_s
        for sl in range(1, 8):
            best = None
            for j in range(-60, 61):
                cand = d[sl] + j * 5.0
                e = 0
                for i in its:
                    for s2, v in by_it[i]:
                        if s2 != sl:
                            continue
                        if level_at(u[i] + cand, bits) != v:
                            e += 1
                if best is None or e < best[0]:
                    best = (e, cand)
            d[sl] = best[1]
    # total error
    e = 0
    n = 0
    for i in its:
        for sl, v in by_it[i]:
            n += 1
            if level_at(u[i] + d[sl], bits) != v:
                e += 1
    return u, d, e, n


def main():
    meta, caps = load_dataset()
    ds = []
    for c in caps:
        if c['rep'] == 2:
            continue
        s = linearize(c['capture'])
        bits = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
        nb = len(bits)
        tmax = nb * BIT
        s = [x for x in s if x[0] <= 100]
        d = [0.0, 3.37 * 62.5, 8.47 * 62.5, 11.28 * 62.5, 17.65 * 62.5,
             20.56 * 62.5, 26.09 * 62.5, 30.03 * 62.5]
        # initial u: linear
        u0 = {i: 62.5 * (40.0 * i + 1.4) for i in range(0, 101)}
        u, d, e, n = fit(s, bits, d, u0)
        per = [round(u[i + 1] - u[i], 1) for i in range(0, 95)]
        print(f"{c['pattern']:11s}{c['rep']} err={e:3d}/{n} "
              f"d={[round(x,1) for x in d]}")
        print(f"    periods: {per[:48]}")
        ds.append(d)
    print("mean d:", [round(sum(x[k] for x in ds) / len(ds), 1) for k in range(8)])


main()
