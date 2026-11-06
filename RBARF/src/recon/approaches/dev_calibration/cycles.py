"""Enumerate integer-cycle gap layouts.

cap_code.s documents inter-sample gaps [4,4,4,4,4,6,5,6] cycles = 37 cy,
but the measured loop is ~40.1 cy.  Distribute the extra cycles over the
eight gaps in every possible way and score each layout on the real
captures with only (t0, eps) free per capture.
"""
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


def fit_all(caps, o, G, h1, h0, lo=2480.0, hi=2536.0, step=0.3,
            t0lo=-100.0, t0hi=560.0, t0step=8.0, nuis=None):
    ks = np.arange(lo, hi, step) / G
    t0s = np.arange(t0lo, t0hi, t0step)
    tot = 0
    out = {}
    for c in caps:
        A = F.A_of(c, o, G, 0.0)
        B = F.edges_of(c["bits"], h1, h0)
        if nuis and c["key"] in nuis:
            t0, k = nuis[c["key"]][:2]
        else:
            _, t0, k, _ = F.fit_tk_grid(A, B, c["alv"], t0s, ks)
        v, m, t0, k = F.polish_tk(A, B, c["alv"], t0, k)
        out[c["key"]] = (t0, k, m)
        tot += m
    return tot, out


def compositions(total, parts):
    for cut in itertools.combinations(range(total + parts - 1), parts - 1):
        prev = -1
        res = []
        for x in cut:
            res.append(x - prev - 1)
            prev = x
        res.append(total + parts - 2 - prev)
        yield res


def main():
    meta, caps = F.load()
    N = sum(c["an"] for c in caps)
    h1, h0 = float(sys.argv[1]) if len(sys.argv) > 1 else 750.0, \
        float(sys.argv[2]) if len(sys.argv) > 2 else 375.0
    res = []
    t = time.time()
    for extra in (2, 3, 4):
        for e in compositions(extra, 8):
            gaps = BASE + np.array(e)
            o, G = offsets(gaps)
            tot, nu = fit_all(caps, o, G, h1, h0)
            res.append((tot, list(map(int, gaps)), nu))
            print(f"  gaps={list(map(int,gaps))} sum={int(gaps.sum())} "
                  f"act={100*tot/N:.3f}%", flush=True)
    res.sort(key=lambda r: -r[0])
    print(f"[{time.time()-t:.0f}s] BEST")
    for tot, g, _ in res[:10]:
        print(f"   {g} -> {100*tot/N:.3f}%")
    json.dump([[r[0], r[1]] for r in res], open("cycles_scan.json", "w"))


if __name__ == "__main__":
    main()
