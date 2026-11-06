"""E13: GLOBAL slot calibration driven ONLY by the anchor bits.

The 64 known frame bits (header+trailer) give ~256 labelled samples per
capture.  Maximising anchor agreement over the global grid (G, P, h1, h0)
uses no ground truth at all -- it is a legal decoder-side calibration.
Afterwards we check what it did to the (unseen) payload.
"""
import json

import numpy as np

from common import load, bits_of, HEADER, TRAILER, BIT_NS

G0 = 40.0
P0 = [0., 4., 8., 12., 16., 20., 26., 31.]
HDR = bits_of(HEADER).astype(bool)
TRL = bits_of(TRAILER).astype(bool)
T_TRL0 = 160 * BIT_NS
T_END = 192 * BIT_NS
N_HDR = 112
NW = 900

meta, caps = load()
FIT = [c for c in caps if c["rep"] == 0]
for c in caps:
    c["itf"] = c["it"][:NW].astype(float)
    c["slf"] = c["sl"][:NW]
    c["ob"] = c["lv"][:NW].astype(bool)

T0S = np.arange(0., 460., 4.)
KS = np.arange(60.0, 65.0, 0.01)


def anchor_vec(u, ob, t0s, ks, h1, h0):
    """bipolar anchor score over the (t0, kappa) grid -- vectorised."""
    S = np.empty((len(t0s), len(ks)))
    for b, k in enumerate(ks):
        t = t0s[:, None] + k * u[None, :]
        j = np.floor(t / BIT_NS).astype(int)
        inh = (j >= 0) & (j < 32)
        int_ = (j >= 160) & (j < 192)
        jj = np.clip(j, 0, 191)
        bits = np.where(jj < 32, HDR[np.clip(jj, 0, 31)],
                        TRL[np.clip(jj - 160, 0, 31)])
        p = t - jj * BIT_NS
        pred = p < np.where(bits, h1, h0)
        good = pred == ob[None, :]
        S[:, b] = np.where(inh | int_, np.where(good, 1, -1), 0).sum(1)
    return S


def fit_one(c, G, P, h1, h0, t0=None, k=None):
    u = c["itf"] * G + np.asarray(P)[c["slf"]]
    if t0 is None:
        S = anchor_vec(u, c["ob"], T0S, KS, h1, h0)
        a, b = np.unravel_index(np.argmax(S), S.shape)
        return float(S[a, b]), float(T0S[a]), float(KS[b]), u
    t0s = np.arange(max(0., t0 - 24), t0 + 24, 1.0)
    ks = np.arange(k - 0.12, k + 0.12, 0.002)
    S = anchor_vec(u, c["ob"], t0s, ks, h1, h0)
    a, b = np.unravel_index(np.argmax(S), S.shape)
    return float(S[a, b]), float(t0s[a]), float(ks[b]), u


WARM = {}


def total(G, P, h1, h0, sub=None, save=False):
    tot = 0
    for c in (sub or FIT):
        w = WARM.get(c["key"])
        s, t0, k, _ = fit_one(c, G, P, h1, h0,
                              *(w if w else (None, None)))
        if save:
            WARM[c["key"]] = (t0, k)
        tot += s
    return tot


def main():
    G, P, h1, h0 = G0, list(P0), 750.0, 375.0
    tot = total(G, P, h1, h0, save=True)
    NA = 256 * len(FIT)
    print(f"seed anchor score {tot} (~{100*(tot/NA+1)/2:.2f}% match)", flush=True)
    for step in (1.0, 0.5, 0.25, 0.125):
        for rnd in range(4):
            prev = tot
            for s in range(1, 8):
                cur = P[s]
                best = (tot, cur)
                for v in np.arange(cur - 2 * step, cur + 2 * step + 1e-9, step):
                    t = total(G, P[:s] + [float(v)] + P[s + 1:], h1, h0)
                    if t > best[0]:
                        best = (t, float(v))
                P[s] = best[1]
                tot = total(G, P, h1, h0, save=True)
            for nm, rg in (("h1", 40.), ("h0", 60.)):
                cur = h1 if nm == "h1" else h0
                best = (tot, cur)
                for v in np.arange(cur - rg, cur + rg + 1e-9, rg / 4):
                    t = total(G, P, v if nm == "h1" else h1,
                              h0 if nm == "h1" else v)
                    if t > best[0]:
                        best = (t, float(v))
                if nm == "h1":
                    h1 = best[1]
                else:
                    h0 = best[1]
                tot = total(G, P, h1, h0, save=True)
            cur = G
            best = (tot, cur)
            for v in np.arange(cur - 0.3, cur + 0.301, 0.075):
                t = total(float(v), P, h1, h0)
                if t > best[0]:
                    best = (t, float(v))
            G = best[1]
            tot = total(G, P, h1, h0, save=True)
            print(f"step={step} r{rnd}: {tot} (~{100*(tot/NA+1)/2:.2f}%) "
                  f"G={G:.3f} P={[round(x,3) for x in P]} h1={h1} h0={h0}",
                  flush=True)
            if tot <= prev:
                break
    gaps = [P[i + 1] - P[i] for i in range(7)] + [G - P[7]]
    print(f"FINAL G={G} P={P} h1={h1} h0={h0}")
    print("gaps(cy):", [round(x, 3) for x in gaps],
          " ns@62.5:", [round(x * 62.5, 1) for x in gaps])

    # --- now score the PAYLOAD (held out from the fit) on all 54 captures
    era = errd = err = imp = ex = nb = 0
    for c in caps:
        WARM.pop(c["key"], None)
        s, t0, k, u = fit_one(c, G, P, h1, h0)
        s, t0, k, u = fit_one(c, G, P, h1, h0, t0, k)
        t = t0 + k * u
        ob = c["ob"]
        hard = np.zeros(128, int)
        nd = np.zeros(128, int)
        for j in range(32, 160):
            lo = j * BIT_NS
            m = (t >= lo) & (t < lo + BIT_NS)
            if not m.any():
                continue
            p, o = t[m] - lo, ob[m]
            s1 = int(((p < h1) == o).sum()) - int(((p < h1) != o).sum())
            s0 = int(((p < h0) == o).sum()) - int(((p < h0) != o).sum())
            hard[j - 32] = 1 if s1 > s0 else 0
            nd[j - 32] = int(((p >= h0) & (p < h1)).sum())
            imp += int(((p >= h1) & o).sum())
        truth = c["bits"][32:160]
        bad = hard != truth
        dec = nd > 0
        nb += 128
        era += int((~dec).sum())
        errd += int((bad & dec).sum())
        err += int(bad.sum())
        ex += int(not bad.any())
        print(f"  {c['key']:14s} anch={s:4.0f}/256 t0={t0:6.1f} k={k:.4f} "
              f"loop={G*k:7.1f} era={int((~dec).sum()):3d} "
              f"errdec={int((bad&dec).sum()):3d}")
    print(f"\nPAYLOAD: erasures {100*era/nb:.2f}%  "
          f"BER(dec) {100*errd/max(nb-era,1):.2f}%  BER {100*err/nb:.2f}%  "
          f"impossible/cap {imp/len(caps):.1f}  exact {ex}/{len(caps)}")
    json.dump({"G": G, "P": P, "h1": h1, "h0": h0}, open("e13_grid.json", "w"))


main()
