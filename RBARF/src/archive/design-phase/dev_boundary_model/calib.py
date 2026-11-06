"""Global fit of the 8 intra-loop slot phases + per-capture (L, B).

Model:  t(it, slot) = B + L * (it + f[slot]),  f[0] == 0
f is a hardware property (fit globally); L, B are per-capture.
Objective: agreement of observed levels with the known frame waveform on
the exact 1250 ns grid.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness import linearize, load_dataset  # noqa: E402

BIT = 1250.0
T0H = 350.0
T1H = 700.0
NB = 192


def frame_bits(frame_hex):
    fb = bytes.fromhex(frame_hex)
    return np.array([(b >> (7 - k)) & 1 for b in fb for k in range(8)])


class Cap:
    def __init__(self, cap, max_it=110):
        s = linearize(cap["capture"])
        s = [x for x in s if x[0] <= max_it]
        self.it = np.array([x[0] for x in s], dtype=float)
        self.sl = np.array([x[1] for x in s], dtype=int)
        self.v = np.array([x[2] for x in s], dtype=int)
        bits = frame_bits(cap["frame"])
        self.th = np.where(bits == 1, T1H, T0H)
        self.pattern = cap["pattern"]
        self.rep = cap["rep"]
        self.payload = cap["payload"]
        # index of the last high sample (for L bootstrap)
        allsam = linearize(cap["capture"])
        hi = [k for k, x in enumerate(allsam) if x[2] == 1]
        self.last_hi = allsam[hi[-1]] if hi else None

    def pred(self, t):
        idx = np.floor(t / BIT).astype(int)
        ok = (idx >= 0) & (idx < NB)
        idc = np.clip(idx, 0, NB - 1)
        return (ok & ((t - idc * BIT) < self.th[idc])).astype(int)

    def bad(self, L, B, farr):
        t = B + L * (self.it + farr[self.sl])
        m = (t >= -3000) & (t <= NB * BIT + 3000)
        return int(np.sum(self.pred(t[m]) != self.v[m])), int(m.sum())

    def bad_slot(self, L, B, farr, s):
        m0 = self.sl == s
        t = B + L * (self.it[m0] + farr[s])
        m = (t >= -3000) & (t <= NB * BIT + 3000)
        return int(np.sum(self.pred(t[m]) != self.v[m0][m]))


def fit_LB(c, farr):
    # bootstrap L from the last high sample (~t = 239450 - a bit)
    it, sl, _ = c.last_hi
    approx_t = NB * BIT - BIT + T1H - 150.0     # ~239300
    L0 = approx_t / (it + farr[sl]) if (it + farr[sl]) > 0 else 2507.3
    best = None
    for Li in range(-60, 61):
        L = L0 + Li * 0.5
        for Bi in range(-30, 61):
            B = Bi * 10.0
            b, tot = c.bad(L, B, farr)
            if best is None or b < best[0]:
                best = (b, L, B)
    b, L, B = best
    for stepL, stepB in ((0.25, 4.0), (0.08, 1.5), (0.03, 0.5), (0.01, 0.2)):
        for _ in range(200):
            improved = False
            for dL in (-stepL, 0, stepL):
                for dB in (-stepB, 0, stepB):
                    if dL == 0 and dB == 0:
                        continue
                    nb, _ = c.bad(L + dL, B + dB, farr)
                    if nb < b:
                        b, L, B = nb, L + dL, B + dB
                        improved = True
            if not improved:
                break
    return b, L, B


def main():
    meta, caps = load_dataset()
    f = [p / 37.0 for p in meta["sample_cycle_positions"]]
    f = [x - f[0] for x in f]
    farr = np.array(f)
    train = [c for c in caps if c["rep"] in (0, 1)]
    data = [Cap(c) for c in train]

    for rnd in range(10):
        LBs = [fit_LB(c, farr) for c in data]
        totbad = sum(x[0] for x in LBs)
        tot = sum(c.bad(L, B, farr)[1] for c, (_, L, B) in zip(data, LBs))
        print(f"round {rnd}: mismatch {totbad}/{tot} = {totbad/tot:.4%}")
        print("   f cycles:", [round(x * 40.117, 3) for x in farr])
        print(f"   L {min(x[1] for x in LBs):.2f}..{max(x[1] for x in LBs):.2f}"
              f"  B {min(x[2] for x in LBs):.1f}..{max(x[2] for x in LBs):.1f}")
        ps = [sum(c.bad_slot(L, B, farr, s) for c, (_, L, B) in zip(data, LBs))
              for s in range(8)]
        print("   per-slot bad:", ps)

        newf = farr.copy()
        for s in range(1, 8):
            cands = newf[s] + np.arange(-150, 151) * 0.0012
            best_b, best_v = None, newf[s]
            for cv in cands:
                tf = newf.copy()
                tf[s] = cv
                b = sum(c.bad_slot(L, B, tf, s)
                        for c, (_, L, B) in zip(data, LBs))
                if best_b is None or b < best_b:
                    best_b, best_v = b, cv
            newf[s] = best_v
        if np.max(np.abs(newf - farr)) < 1e-7:
            break
        farr = newf

    print("FINAL f =", [round(float(x), 7) for x in farr])
    print("FINAL cycles =", [round(float(x) * 40.117, 3) for x in farr])
    Path(__file__).with_name("f.json").write_text(json.dumps([float(x) for x in farr]))


if __name__ == "__main__":
    main()
