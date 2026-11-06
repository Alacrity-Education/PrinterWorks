"""Per-capture (lam, beta) fit using ONLY header+trailer known bits.
Then measure fall-phase separability and per-bit evidence counts."""
import json, math
import numpy as np
from collections import Counter, defaultdict
from common import *

meta, caps = load_dataset()
G = json.load(open("geom.json"))
PHI = np.array([x / 2500.0 for x in G["o"]])
H0, H1 = 0.28, 0.56
HB = np.array([H0, H1])

HDRBITS = np.array([(b >> (7 - k)) & 1 for b in HDR for k in range(8)])
TRLBITS = np.array([(b >> (7 - k)) & 1 for b in TRL for k in range(8)])
KNOWN = np.full(192, -1, dtype=np.int8)
KNOWN[:32] = HDRBITS
KNOWN[160:] = TRLBITS


def fit_lam_beta(cc, vv, lam_rng=(1.85, 2.16), n_lam=311, n_b=241,
                 beta_rng=(-1.0, 1.0), rounds=4):
    lo_l, hi_l = lam_rng
    lo_b, hi_b = beta_rng
    best = None
    for r in range(rounds):
        lams = np.linspace(lo_l, hi_l, n_lam)
        betas = np.linspace(lo_b, hi_b, n_b)
        for lam in lams:
            xb = cc * lam
            for beta in betas:
                x = xb + beta
                k = np.floor(x).astype(np.int64)
                m = (k >= 0) & (k < 192)
                kk = k[m]
                kn = KNOWN[kk]
                m2 = kn >= 0
                if not m2.any():
                    continue
                frac = (x[m] - kk)[m2]
                pred = (frac < HB[kn[m2]]).astype(np.int8)
                mis = int((pred != vv[m][m2]).sum())
                tot = int(m2.sum())
                sc = mis + 0.002 * (2000 - tot)
                if best is None or sc < best[0]:
                    best = (sc, lam, beta, mis, tot)
        _, lam, beta, mis, tot = best
        dl = (hi_l - lo_l) / (n_lam - 1)
        db = (hi_b - lo_b) / (n_b - 1)
        lo_l, hi_l = lam - 3 * dl, lam + 3 * dl
        lo_b, hi_b = beta - 3 * db, beta + 3 * db
        n_lam, n_b = 25, 25
    return best[1], best[2], best[3], best[4]


rows = []
FALL = defaultdict(list)
EV = defaultdict(Counter)
BITERR = Counter()
for c in caps:
    s = linearize(c["capture"])
    bits = np.array(frame_bits(c["payload"]))
    it = np.array([a for a, _, _ in s], dtype=float)
    sl = np.array([b for _, b, _ in s])
    vv = np.array([v for _, _, v in s], dtype=np.int8)
    cc = it + PHI[sl]
    lam, beta, mis, tot = fit_lam_beta(cc, vv)
    x = cc * lam + beta
    k = np.floor(x).astype(np.int64)
    m = (k >= 0) & (k < 192)
    frac = x[m] - k[m]
    pred = (frac < HB[bits[k[m]]]).astype(np.int8)
    allmis = int((pred != vv[m]).sum())
    rows.append((c["pattern"], c["rep"], float(lam), float(beta), mis, tot,
                 allmis, int(m.sum())))
    # per-bit evidence: samples with frac in [H0,H1)
    disc = (frac >= H0) & (frac < H1)
    for b in range(192):
        sel = disc & (k[m] == b)
        n = int(sel.sum())
        agree = int((vv[m][sel] == bits[b]).sum())
        EV[bits[b]][(n, n - agree)] += 1
        if n == 0:
            BITERR[("none", bits[b])] += 1
        else:
            maj = 1 if vv[m][sel].sum() * 2 > n else 0
            if maj != bits[b]:
                BITERR[("wrong", bits[b])] += 1

print("=== hdr/trl fit ===")
for r in sorted(rows, key=lambda r: -r[6])[:8]:
    print("  worst allmis:", r)
lams = [r[2] for r in rows]
print("lam min/med/max %.5f %.5f %.5f" % (min(lams), sorted(lams)[27], max(lams)))
print("hdr/trl mismatch total", sum(r[4] for r in rows), "of", sum(r[5] for r in rows))
print("in-frame mismatch total", sum(r[6] for r in rows), "of", sum(r[7] for r in rows))
print("\n=== per-bit discriminating-window evidence ===")
for b in (0, 1):
    tot = sum(EV[b].values())
    h = Counter()
    for (n, dis), cnt in EV[b].items():
        h[n] += cnt
    print(f" bit={b} tot={tot} n_disc hist={dict(sorted(h.items()))}")
    dd = Counter()
    for (n, dis), cnt in EV[b].items():
        if dis:
            dd[(n, dis)] += cnt
    print(f"        disagreeing: {dict(sorted(dd.items()))}")
print(" majority-vote errors:", dict(BITERR))
json.dump(rows, open("fit.json", "w"))
