"""Global calibration by alternating exact profiling.

Key structural trick: for fixed per-capture (t0,k) and fixed d, the eight
slot offsets o[0..7] decouple -- slot s only appears in its own samples --
so each o[s] can be optimised EXACTLY by a 1-D scan over the shared
objective (total matching samples over all 54 captures).  Alternate that
with per-capture (t0,k) refinement and 1-D scans of h1/h0/d.
"""
import json
import sys
import time

import numpy as np

import model
from model import wire_levels

G = 2500.0                      # nominal loop length in ns at 16 MHz
ACT = 102                       # iterations that can carry frame signal


def prepare(caps):
    for c in caps:
        Ncum = np.concatenate([[0], np.cumsum(c["lv"].astype(np.int64))[:-1]])
        keep = c["it"] < ACT
        c["ait"] = c["it"][keep].astype(float)
        c["asl"] = c["sl"][keep]
        c["alv"] = c["lv"][keep]
        c["aN"] = Ncum[keep].astype(float)
        c["na"] = int(keep.sum())
        c["by_slot"] = [np.nonzero(c["asl"] == s)[0] for s in range(8)]
    return caps


def A_full(c, o, d):
    o = np.asarray(o, float)
    return c["ait"] * G + o[c["asl"]] - d * c["aN"]


def nmatch(c, o, d, t0, k, h1, h0):
    t = t0 + k * A_full(c, o, d)
    return int(np.count_nonzero(wire_levels(t, c["bits"], h1, h0) == c["alv"]))


def coarse_tk(c, o, d, h1, h0, ks, t0s):
    A = A_full(c, o, d)
    bits, lv = c["bits"], c["alv"]
    best = (-1, 0.0, 1.0)
    for k in ks:
        base = k * A
        for t0 in t0s:
            m = int(np.count_nonzero(wire_levels(t0 + base, bits, h1, h0) == lv))
            if m > best[0]:
                best = (m, t0, k)
    return best


def polish_tk(c, o, d, h1, h0, t0, k, st=16.0, sk=3e-5):
    A = A_full(c, o, d)
    bits, lv = c["bits"], c["alv"]

    def sc(t0_, k_):
        return int(np.count_nonzero(
            wire_levels(t0_ + k_ * A, bits, h1, h0) == lv))
    m = sc(t0, k)
    while st > 5e-4 or sk > 1e-9:
        found = None
        for dt, dk in ((st, 0.0), (-st, 0.0), (0.0, sk), (0.0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = sc(t0 + dt, k + dk)
            if mm > m:
                m, found = mm, (t0 + dt, k + dk)
        if found is None:
            st /= 2.0
            sk /= 2.0
        else:
            t0, k = found
    return m, t0, k


def slot_profile(caps, nuis, s, d, h1, h0, ovals):
    """Total matches over all captures for slot s at each candidate offset."""
    tot = np.zeros(len(ovals), dtype=np.int64)
    for c in caps:
        idx = c["by_slot"][s]
        t0, k = nuis[c["key"]][:2]
        base = t0 + k * (c["ait"][idx] * G - d * c["aN"][idx])
        t = base[:, None] + k * ovals[None, :]
        pred = wire_levels(t.ravel(), c["bits"], h1, h0).reshape(t.shape)
        tot += (pred == c["alv"][idx][:, None]).sum(axis=0)
    return tot


def total(caps, nuis):
    return sum(v[2] for v in nuis.values()) / sum(c["na"] for c in caps)


def run(caps, o, d, h1, h0, rounds=14, verbose=True):
    ks = np.arange(0.9950, 1.0165, 2.5e-5)
    t0s = np.arange(-250.0, 400.0, 12.0)
    nuis = {}
    for c in caps:
        m, t0, k = coarse_tk(c, o, d, h1, h0, ks, t0s)
        m, t0, k = polish_tk(c, o, d, h1, h0, t0, k)
        nuis[c["key"]] = (t0, k, m)
    if verbose:
        print(f"  after init (t0,k): {total(caps, nuis)*100:.3f}%", flush=True)

    for r in range(rounds):
        # --- exact profiling of each slot offset -----------------------
        for s in range(8):
            lo = max(0.0, o[s] - 420.0)
            hi = min(G + 60.0, o[s] + 420.0)
            step = 1.0 if r < 3 else 0.125
            ovals = np.arange(lo, hi, step)
            tot = slot_profile(caps, nuis, s, d, h1, h0, ovals)
            o[s] = float(ovals[int(np.argmax(tot))])
        o.sort()
        # --- 1-D scans for h1, h0, d ----------------------------------
        for name in ("h1", "h0", "d"):
            cur = {"h1": h1, "h0": h0, "d": d}[name]
            step = {"h1": 8.0, "h0": 8.0, "d": 2.0}[name] if r < 3 else \
                   {"h1": 0.5, "h0": 0.5, "d": 0.1}[name]
            cands = cur + np.arange(-14, 15) * step
            best = (-1, cur)
            for v in cands:
                hh1 = v if name == "h1" else h1
                hh0 = v if name == "h0" else h0
                dd = v if name == "d" else d
                if hh1 <= 0 or hh0 <= 0 or hh1 > 1200 or hh0 > 1200:
                    continue
                tt = sum(nmatch(c, o, dd, *nuis[c["key"]][:2], hh1, hh0)
                         for c in caps)
                if tt > best[0]:
                    best = (tt, v)
            if name == "h1":
                h1 = best[1]
            elif name == "h0":
                h0 = best[1]
            else:
                d = best[1]
        # --- refresh nuisances ----------------------------------------
        for c in caps:
            t0, k = nuis[c["key"]][:2]
            m, t0, k = polish_tk(c, o, d, h1, h0, t0, k)
            nuis[c["key"]] = (t0, k, m)
        if verbose:
            print(f"  round {r}: {total(caps, nuis)*100:.4f}%  "
                  f"o={[round(x,1) for x in o]} d={d:.3f} "
                  f"h1={h1:.2f} h0={h0:.2f}", flush=True)
    return o, d, h1, h0, nuis


def main():
    meta, caps = model.load()
    caps = prepare(caps)
    o = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0]
    t = time.time()
    o, d, h1, h0, nuis = run(caps, list(o), 0.0, 750.0, 375.0)
    print(f"final {total(caps,nuis)*100:.4f}%  [{time.time()-t:.0f}s]")
    json.dump({"o": o, "d": d, "h1": h1, "h0": h0,
               "nuis": {k: list(v) for k, v in nuis.items()}},
              open("stage2.json", "w"), indent=1)


if __name__ == "__main__":
    main()
