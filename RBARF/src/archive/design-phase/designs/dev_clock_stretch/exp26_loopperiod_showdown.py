"""Fair, apples-to-apples scan of the loop period.

Model: t(i,s) = phi_c + (i*G + o[s]) * sc_c,  levels from a waveform with
effective high widths (h0,h1).  o[], h0, h1 are GLOBAL; (phi_c, sc_c) are
per capture.  Scan G; at each G re-optimise per-capture (phi, sc) finely
and report the IN-FRAME sample match (first 100 loops only).

Two o[] hypotheses are compared at every G:
  - dev_calibration's fitted o[] (rescaled to G)
  - the documented [1,5,9,13,17,21,27,32]/40 fractions
"""
import json
import numpy as np
from common import load_all

CAL = json.load(open("/home/alex.lucaci/Projects/RBARF/new-implementation/"
                     "recon/approaches/dev_calibration/final.json"))
O_CAL_FRAC = np.array(CAL["o"]) / CAL["G"]
O_DOC_FRAC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
H1, H0 = CAL["h1"], CAL["h0"]
BIT = 1250.0

meta, caps = load_all()
CS = []
for c in caps:
    m = c["it"] < 100
    CS.append(dict(it=c["it"][m].astype(float), slot=c["slot"][m],
                   lev=c["lev"][m], bits=c["bits"]))
N = sum(len(c["lev"]) for c in CS)


def wv(bits, t, h1, h0):
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < len(bits))
    kc = np.clip(k, 0, len(bits) - 1)
    hi = np.where(bits[kc] == 1, h1, h0)
    return np.where(ok & (t - k*BIT < hi) & (t >= 0), 1, 0).astype(np.int8)


def best_cap(c, Leff, ofrac, h1, h0):
    """optimise (phi, per-capture scale) for a given effective loop Leff."""
    u = c["it"] + ofrac[c["slot"]]
    best = (-1, 0., 1.)
    for sc in np.arange(0.997, 1.0031, 0.0005):
        base = u * (Leff * sc)
        for phi in np.arange(-400., 500., 12.5):
            v = int((wv(c["bits"], phi + base, h1, h0) == c["lev"]).sum())
            if v > best[0]:
                best = (v, phi, sc)
    # polish
    v, phi, sc = best
    for _ in range(3):
        for dphi in np.arange(-15, 15.1, 1.5):
            for dsc in np.arange(-0.0006, 0.00061, 0.0001):
                vv = int((wv(c["bits"], phi+dphi + u*(Leff*(sc+dsc)), h1, h0)
                          == c["lev"]).sum())
                if vv > v:
                    v, phi, sc = vv, phi+dphi, sc+dsc
    return v


for tag, ofrac, h1, h0 in (("cal-o, cal-h", O_CAL_FRAC, H1, H0),
                           ("doc-o, cal-h", O_DOC_FRAC, H1, H0),
                           ("cal-o, exact-h", O_CAL_FRAC, 700.0, 350.0)):
    print(f"\n== {tag} ==")
    for Leff in (2470., 2480., 2490., 2498., 2505., 2515., 2520., 2525.,
                 2527.5, 2530., 2540., 2560.):
        tot = sum(best_cap(c, Leff, ofrac, h1, h0) for c in CS)
        print(f"  Leff={Leff:8.1f}  in-frame match = {tot/N:.4%}")
