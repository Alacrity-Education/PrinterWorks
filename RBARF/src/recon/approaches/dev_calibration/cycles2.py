"""Fast enumeration of integer-cycle gap layouts (vectorised)."""
import itertools
import json
import sys
import time

import numpy as np

import fitlib as F

CY = 62.5
BASE = np.array([4, 4, 4, 4, 4, 6, 5, 6])


def offsets(gaps):
    g = np.asarray(gaps, float) * CY
    return np.concatenate([[0.0], np.cumsum(g)[:-1]]), float(g.sum())


def best_tk(A, B, lv, Ltargets, G, t0s):
    """Vectorised (t0, loop-period) grid; returns (matches, t0, k)."""
    best = (-1, 0.0, 1.0)
    for Lt in Ltargets:
        k = Lt / G
        T = t0s[:, None] + k * A[None, :]
        pred = (np.searchsorted(B, T.ravel(), side="right") & 1
                ).reshape(T.shape).astype(np.int8)
        m = (pred == lv[None, :]).sum(axis=1)
        j = int(np.argmax(m))
        if m[j] > best[0]:
            best = (int(m[j]), float(t0s[j]), float(k))
    return best


def score_layout(caps, gaps, h1, h0, Lc, t0s, Lspan=14.0, Lstep=0.35):
    o, G = offsets(gaps)
    tot = 0
    nu = {}
    for c in caps:
        A = F.A_of(c, o, G, 0.0)
        B = F.edges_of(c["bits"], h1, h0)
        L0 = Lc[c["key"]]
        Lt = np.arange(L0 - Lspan, L0 + Lspan, Lstep)
        m, t0, k = best_tk(A, B, c["alv"], Lt, G, t0s)
        v, m, t0, k = F.polish_tk(A, B, c["alv"], t0, k, st=8.0, sk=1.5e-5)
        nu[c["key"]] = (t0, k, m)
        tot += m
    return tot, nu


def compositions(total, parts):
    for cut in itertools.combinations(range(total + parts - 1), parts - 1):
        prev = -1
        res = []
        for x in cut:
            res.append(x - prev - 1)
            prev = x
        res.append(total + parts - 2 - prev)
        yield res


def calibrate_loops(caps, h1, h0):
    """Rough per-capture effective loop period, layout independent."""
    o, G = offsets(BASE + np.array([0, 0, 0, 0, 0, 1, 1, 1]))
    t0s = np.arange(-120.0, 620.0, 6.0)
    Lt = np.arange(2480.0, 2540.0, 0.25)
    out = {}
    for c in caps:
        A = F.A_of(c, o, G, 0.0)
        B = F.edges_of(c["bits"], h1, h0)
        m, t0, k = best_tk(A, B, c["alv"], Lt, G, t0s)
        out[c["key"]] = k * G
    return out


def main():
    h1 = float(sys.argv[1]) if len(sys.argv) > 1 else 750.0
    h0 = float(sys.argv[2]) if len(sys.argv) > 2 else 375.0
    extras = [int(x) for x in sys.argv[3:]] or [3]
    meta, caps = F.load()
    N = sum(c["an"] for c in caps)
    t = time.time()
    Lc = calibrate_loops(caps, h1, h0)
    print(f"loop calib [{time.time()-t:.0f}s] "
          f"median={np.median(list(Lc.values())):.2f}", flush=True)
    t0s = np.arange(-140.0, 640.0, 6.0)
    res = []
    for extra in extras:
        for e in compositions(extra, 8):
            gaps = BASE + np.array(e)
            tot, nu = score_layout(caps, gaps, h1, h0, Lc, t0s)
            res.append((tot, [int(x) for x in gaps]))
            print(f"  {[int(x) for x in gaps]} sum={int(gaps.sum())} "
                  f"act={100*tot/N:.3f}%", flush=True)
    res.sort(key=lambda r: -r[0])
    print(f"[{time.time()-t:.0f}s] TOP")
    for tot, g in res[:15]:
        print(f"   {g} -> {100*tot/N:.3f}%")
    json.dump(res, open(f"cycles_scan_{h1:.0f}_{h0:.0f}.json", "w"))


if __name__ == "__main__":
    main()
