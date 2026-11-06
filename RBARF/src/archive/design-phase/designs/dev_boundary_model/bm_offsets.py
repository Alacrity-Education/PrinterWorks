"""Global intra-loop slot-offset fit, decoupled from the clock.

Each loop gets a FREE phase phi_i, so any per-capture scale/phase/drift is
absorbed; what remains is purely the intra-loop geometry O[0..7] plus the
effective high widths h1,h0.  Minimise total mismatched samples over all
54 captures, loops 0..93 (fully inside the frame).
"""
import json
import sys

import numpy as np

from bm_common import BIT_NS, load

CY = 62.5
DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) * CY
P = np.arange(0.0, 1250.0, 1.0)
NL = 94


class Cap:
    def __init__(self, c):
        self.key = c["key"]
        self.bits = c["bits"]
        lv = np.full((NL, 8), -1, np.int8)
        for k in range(len(c["lv"])):
            i, s = c["it"][k], c["sl"][k]
            if i < NL:
                lv[i, s] = c["lv"][k]
        self.lv = lv
        self.I = np.arange(NL, dtype=float)[:, None]
        self.hw = None

    def prep(self, h1, h0):
        b = self.bits
        self.hwv = np.where(b == 1, h1, h0)
        self.nb = len(b)

    def wl(self, t):
        j = np.floor(t / BIT_NS).astype(np.int64)
        ok = (j >= 0) & (j < self.nb)
        jc = np.clip(j, 0, self.nb - 1)
        return (ok & ((t - jc * BIT_NS) < self.hwv[jc])).astype(np.int8)

    def mism(self, O):
        """min over phase of mismatched samples, per loop -> (total, per-loop)."""
        acc = np.zeros((NL, len(P)), np.int16)
        for s in range(8):
            t = 2500.0 * self.I + O[s] + P[None, :]
            pred = self.wl(t)
            acc += (pred != self.lv[:, s][:, None]).astype(np.int16)
        m = acc.min(axis=1)
        return int(m.sum()), m, acc


def total(caps, O):
    return sum(c.mism(O)[0] for c in caps)


def main():
    meta, raw = load()
    caps = [Cap(c) for c in raw]
    h1, h0 = 750.0, 375.0
    for c in caps:
        c.prep(h1, h0)
    O = DOC.copy()
    best = total(caps, O)
    N = NL * 8 * len(caps)
    print(f"seed DOC: {best}/{N} = {100*best/N:.3f}%", flush=True)

    for step in (32.0, 16.0, 8.0, 4.0, 2.0, 1.0, 0.5):
        for rnd in range(10):
            prev = best
            for s in range(1, 8):          # O[0] pinned (absorbed by phase)
                base = O[s]
                cand = base + np.arange(-6, 7) * step
                for v in cand:
                    O[s] = v
                    t = total(caps, O)
                    if t < best:
                        best, base = t, v
                O[s] = base
            for nm in ("h1", "h0"):
                cur = h1 if nm == "h1" else h0
                keep = cur
                for v in cur + np.arange(-6, 7) * step:
                    for c in caps:
                        c.prep(v if nm == "h1" else h1, h0 if nm == "h1" else v)
                    t = total(caps, O)
                    if t < best:
                        best, keep = t, v
                if nm == "h1":
                    h1 = keep
                else:
                    h0 = keep
                for c in caps:
                    c.prep(h1, h0)
            print(f"step{step:5.1f} r{rnd}: {best}/{N} = {100*best/N:.3f}%  "
                  f"O={[round(x,1) for x in O]} h1={h1:.1f} h0={h0:.1f}",
                  flush=True)
            if best >= prev:
                break

    gaps = list(np.diff(O)) + [2500.0 - O[7] + O[0]]
    print("gaps ns:", [round(x, 1) for x in gaps])
    print("gaps cy:", [round(x / CY, 3) for x in gaps])
    per = {}
    for c in caps:
        tt, m, _ = c.mism(O)
        per[c.key] = [int(tt), [int(x) for x in m]]
    json.dump(dict(O=list(O), h1=h1, h0=h0, best=best, N=N, per=per),
              open("bm_offsets.json", "w"), indent=1)


if __name__ == "__main__":
    main()
