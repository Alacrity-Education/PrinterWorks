"""Integer-cycle intra-loop geometry fit (free per-loop phase).

O[s] = tau * (C[s] - dcy * Hin(i,s)) with C integer cycle positions,
Hin = HIGH samples earlier in the SAME loop (the BTJT-skips-NOP effect),
tau = CPU cycle in ns.  Loop phase is free per loop, so this measures
pure intra-loop geometry, independent of clock scale/phase/drift.
"""
import itertools
import json
import sys

import numpy as np

from bm_common import BIT_NS, load

P = np.arange(0.0, 1250.0, 1.0)
NL = 94


class Cap:
    def __init__(self, c):
        self.key = c["key"]
        self.bits = c["bits"]
        lv = np.full((NL, 8), 0, np.int8)
        seen = np.zeros((NL, 8), bool)
        for k in range(len(c["lv"])):
            i, s = c["it"][k], c["sl"][k]
            if i < NL:
                lv[i, s] = c["lv"][k]
                seen[i, s] = True
        assert seen.all()
        self.lv = lv
        self.Hin = np.concatenate([np.zeros((NL, 1)), np.cumsum(lv, axis=1)[:, :-1]],
                                  axis=1).astype(float)
        self.I = np.arange(NL, dtype=float)[:, None]

    def prep(self, h1, h0):
        self.hwv = np.where(self.bits == 1, h1, h0)
        self.nb = len(self.bits)

    def wl(self, t):
        j = np.floor(t / BIT_NS).astype(np.int64)
        ok = (j >= 0) & (j < self.nb)
        jc = np.clip(j, 0, self.nb - 1)
        return (ok & ((t - jc * BIT_NS) < self.hwv[jc])).astype(np.int8)

    def mism(self, C, tau, dcy):
        acc = np.zeros((NL, len(P)), np.int16)
        for s in range(8):
            off = tau * (C[s] - dcy * self.Hin[:, s])[:, None]
            t = 2500.0 * self.I + off + P[None, :]
            acc += (self.wl(t) != self.lv[:, s][:, None]).astype(np.int16)
        return int(acc.min(axis=1).sum())


def total(caps, C, tau, dcy):
    return sum(c.mism(C, tau, dcy) for c in caps)


def main():
    meta, raw = load()
    caps = [Cap(c) for c in raw]
    h1, h0 = 750.0, 375.0
    for c in caps:
        c.prep(h1, h0)
    N = NL * 8 * len(caps)

    best = None
    for dcy in (0, 1, -1):
        C = [1, 5, 9, 13, 17, 21, 27, 32]
        for tau in (62.5,):
            t = total(caps, C, tau, dcy)
            print(f"DOC C, tau={tau} dcy={dcy}: {t}/{N} = {100*t/N:.3f}%", flush=True)

    # coordinate descent over integer gaps + continuous tau, per dcy
    for dcy in (0, 1, -1):
        C = [1, 5, 9, 13, 17, 21, 27, 32]
        tau = 62.5
        cur = total(caps, C, tau, dcy)
        for rnd in range(12):
            prev = cur
            for s in range(1, 8):
                keep = C[s]
                for v in range(C[s - 1] + 2, C[s - 1] + 10):
                    if s < 7 and v >= C[s + 1] - 1:
                        continue
                    C2 = list(C)
                    C2[s] = v
                    t = total(caps, C2, tau, dcy)
                    if t < cur:
                        cur, keep = t, v
                C[s] = keep
            keep = tau
            for v in tau + np.arange(-8, 9) * 0.25:
                t = total(caps, C, v, dcy)
                if t < cur:
                    cur, keep = t, v
            tau = keep
            print(f"  dcy={dcy} r{rnd}: {cur}/{N} = {100*cur/N:.3f}% "
                  f"C={C} tau={tau:.2f}", flush=True)
            if cur >= prev:
                break
        if best is None or cur < best[0]:
            best = (cur, list(C), tau, dcy)

    cur, C, tau, dcy = best
    # now polish h1/h0
    for rnd in range(6):
        prev = cur
        for nm in ("h1", "h0"):
            keep = h1 if nm == "h1" else h0
            for v in keep + np.arange(-8, 9) * 4.0:
                for c in caps:
                    c.prep(v if nm == "h1" else h1, h0 if nm == "h1" else v)
                t = total(caps, C, tau, dcy)
                if t < cur:
                    cur, keep = t, v
            if nm == "h1":
                h1 = keep
            else:
                h0 = keep
            for c in caps:
                c.prep(h1, h0)
        print(f"  polish r{rnd}: {cur}/{N} = {100*cur/N:.3f}% h1={h1} h0={h0}",
              flush=True)
        if cur >= prev:
            break

    print(f"BEST C={C} tau={tau:.3f} dcy={dcy} h1={h1} h0={h0} "
          f"-> {cur}/{N} = {100*cur/N:.3f}%")
    gaps = list(np.diff(C))
    print("gaps cy (within loop):", gaps, "span", C[7] - C[0])
    O = [tau * x for x in C]
    json.dump(dict(O=O, C=C, tau=tau, dcy=dcy, h1=h1, h0=h0, mism=cur, N=N),
              open("bm_int.json", "w"), indent=1)


if __name__ == "__main__":
    main()
