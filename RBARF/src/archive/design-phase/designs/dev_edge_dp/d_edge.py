"""Per-slot RISE / FALL edge response of the sampler.

Every WS2812 bit starts with a rising edge (the preceding bit always ends
low) and falls at h0 or h1.  For each slot s fit
    P(read high) = Phi((u - dr_s)/sr_s)          near the rise  (u ~ 0)
    P(read high) = Phi((h_b + df_s - u)/sf_s)    near the fall
by 2-D grid MLE over samples within +/-250 ns of the respective edge.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

CAL = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_calibration")
sys.path.insert(0, str(CAL))
import model as CM      # noqa: E402
import final as CF      # noqa: E402

F = json.load(open(CAL / "final.json"))
G, O, W, H1, H0 = F["G"], np.array(F["o"]), np.array(F["w"]), F["h1"], F["h0"]
meta, caps = CM.load()
CF.prepare(caps)

Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))

R = {s: [[], []] for s in range(8)}     # rise: (u, obs)
Fl = {s: [[], []] for s in range(8)}    # fall: (u - h_b, obs)
for c in caps:
    t0, k = F["nuis"][c["key"]][:2]
    t = t0 + k * CF.A_of(c, G, O, W)
    bits = c["bits"]
    j = np.floor(t / 1250.0).astype(int)
    m = (j >= 0) & (j < 192)
    tt = t[m]; jj = j[m]; u = tt - jj * 1250.0; sl = c["sl"][m]; lv = c["lv"][m]
    h = np.where(bits[jj] == 1, H1, H0)
    for s in range(8):
        z = sl == s
        rr = z & (u < 250)
        R[s][0].append(u[rr]); R[s][1].append(lv[rr])
        ff = z & (np.abs(u - h) < 250)
        Fl[s][0].append(u[ff] - h[ff]); Fl[s][1].append(lv[ff])


def fit(x, y, sign):
    """MLE of (delta, sigma) for P(high)=Phi(sign*(x-delta)/sigma)."""
    best = None
    for dl in np.arange(-120, 120.1, 4.0):
        for sg in np.arange(6.0, 140.1, 2.0):
            p = np.clip(Phi(sign * (x - dl) / sg), 1e-9, 1 - 1e-9)
            v = -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
            if best is None or v < best[0]:
                best = (v, dl, sg)
    return best[1], best[2], best[0] / len(x)


print("slot |   rise: delta   sigma   n   |   fall: delta   sigma   n")
out = {}
for s in range(8):
    xr = np.concatenate(R[s][0]); yr = np.concatenate(R[s][1]).astype(float)
    xf = np.concatenate(Fl[s][0]); yf = np.concatenate(Fl[s][1]).astype(float)
    dr, sr, nr = fit(xr, yr, +1.0)
    df, sf, nf = fit(xf, yf, -1.0)
    out[s] = dict(dr=dr, sr=sr, df=df, sf=sf)
    print(f"  {s}  |  {dr:7.1f} {sr:7.1f} {len(xr):5d}  |  "
          f"{df:7.1f} {sf:7.1f} {len(xf):5d}")

xr = np.concatenate([np.concatenate(R[s][0]) for s in range(8)])
yr = np.concatenate([np.concatenate(R[s][1]) for s in range(8)]).astype(float)
xf = np.concatenate([np.concatenate(Fl[s][0]) for s in range(8)])
yf = np.concatenate([np.concatenate(Fl[s][1]) for s in range(8)]).astype(float)
print("\npooled rise:", [round(v, 1) for v in fit(xr, yr, +1.0)])
print("pooled fall:", [round(v, 1) for v in fit(xf, yf, -1.0)])
print("\nempirical P(high) vs u-h at the FALL (25 ns bins):")
for lo in range(-250, 250, 25):
    m = (xf >= lo) & (xf < lo + 25)
    if m.sum():
        print(f"  {lo:5d}..{lo+25:5d} n={m.sum():5d} P={yf[m].mean():.3f}")
print("\nempirical P(high) vs u at the RISE (25 ns bins):")
for lo in range(-250, 250, 25):
    m = (xr >= lo) & (xr < lo + 25)
    if m.sum():
        print(f"  {lo:5d}..{lo+25:5d} n={m.sum():5d} P={yr[m].mean():.3f}")
json.dump(out, open("edgefit.json", "w"), indent=1)
