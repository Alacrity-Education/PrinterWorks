"""Apply the per-slot residual offsets found by the edge-response fit
(o[s] -= delta_fall[s]) and re-measure in-frame agreement + edge widths.
Iterate twice.  Global calibration only (no per-capture oracle beyond the
(t0,k) nuisance refit, which the decoder replaces with its own search)."""
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
G, W, H1, H0 = F["G"], np.array(F["w"]), F["h1"], F["h0"]
O = np.array(F["o"])
meta, caps = CM.load()
CF.prepare(caps)
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))


def A_of(c, o):
    return c["it"] * G + o[c["sl"]] + c["Hc"] @ W


def refit_tk(c, A, t0, k):
    m, t0, k = CF.polish_tk(c, A, H1, H0, t0, k, st=20.0, sk=3e-5)
    return t0, k


def measure(o, nuis, h1=H1, h0=H0):
    tot = n = 0
    Fx = {s: [[], []] for s in range(8)}
    for c in caps:
        A = A_of(c, o)
        t0, k = nuis[c["key"]]
        t = t0 + k * A
        bits = c["bits"]
        j = np.floor(t / 1250.0).astype(int)
        m = (j >= 0) & (j < 192)
        tt = t[m]; jj = j[m]; u = tt - jj * 1250.0
        h = np.where(bits[jj] == 1, h1, h0)
        pred = (u < h).astype(int)
        tot += int((pred == c["lv"][m]).sum()); n += int(m.sum())
        for s in range(8):
            z = (c["sl"][m] == s) & (np.abs(u - h) < 250)
            Fx[s][0].append(u[z] - h[z]); Fx[s][1].append(c["lv"][m][z])
    return tot, n, Fx


def fitfall(x, y):
    best = None
    for dl in np.arange(-140, 140.1, 2.0):
        for sg in np.arange(6.0, 120.1, 2.0):
            p = np.clip(Phi(-(x - dl) / sg), 1e-9, 1 - 1e-9)
            v = -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
            if best is None or v < best[0]:
                best = (v, dl, sg)
    return best[1], best[2]


nuis = {c["key"]: tuple(F["nuis"][c["key"]][:2]) for c in caps}
o = O.copy()
for it in range(4):
    tot, n, Fx = measure(o, nuis)
    d = []; s_ = []
    for s in range(8):
        x = np.concatenate(Fx[s][0]); y = np.concatenate(Fx[s][1]).astype(float)
        dl, sg = fitfall(x, y)
        d.append(dl); s_.append(sg)
    print(f"iter{it}: agree {tot}/{n} = {tot/n:.4f}  "
          f"o={np.round(o,1).tolist()}")
    print(f"        delta_fall={np.round(d,1).tolist()} sigma={np.round(s_,1).tolist()}")
    o = o - np.array(d) * 0.8
    o = o - o[7] + 2000.0            # keep the gauge (o[7] fixed) as in final.json
    nuis = {c["key"]: refit_tk(c, A_of(c, o), *nuis[c["key"]]) for c in caps}
json.dump({"o": o.tolist(), "sigma_fall": s_,
           "nuis": {k: list(v) for k, v in nuis.items()}},
          open("ocorr.json", "w"), indent=1)
