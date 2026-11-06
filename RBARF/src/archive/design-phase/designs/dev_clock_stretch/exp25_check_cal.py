"""Cross-check the dev_calibration fitted model against my loop-period
conclusion.  Try the plausible parameterisations of final.json and report
the sample-level match rate; whichever reproduces their 'rate' tells us
the loop period their fit actually implies."""
import json, itertools
import numpy as np
from common import load_all, wave

d = json.load(open("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/"
                   "approaches/dev_calibration/final.json"))
G = d["G"]; o = np.array(d["o"]); w = np.array(d["w"]); nuis = d["nuis"]
h1, h0 = d["h1"], d["h0"]
print("G", G, "o", o.tolist(), "w", w.tolist(), "h1", h1, "h0", h0,
      "rate", d["rate"])

meta, caps = load_all()


def wv(bits, t, h1=h1, h0=h0, BIT=1250.0):
    t = np.asarray(t, float)
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < len(bits))
    kc = np.clip(k, 0, len(bits) - 1)
    within = t - k * BIT
    hi = np.where(bits[kc] == 1, h1, h0)
    return np.where(ok & (within < hi) & (t >= 0), 1, 0).astype(np.int8)


forms = {
    "phi + (i*G + o[s])*sc":       lambda i, s, phi, sc: phi + (i*G + o[s])*sc,
    "phi + (i*G + o[s])/sc":       lambda i, s, phi, sc: phi + (i*G + o[s])/sc,
    "phi + i*G*sc + o[s]":         lambda i, s, phi, sc: phi + i*G*sc + o[s],
    "phi + (i*G + o[s])*sc  [w]":  None,
}
for name, f in forms.items():
    if f is None:
        continue
    tot = n = 0
    for cap in caps:
        key = f"{cap['pattern']}_{cap['rep']}"
        if key not in nuis:
            continue
        phi, sc, _ = nuis[key]
        t = f(cap["it"].astype(float), cap["slot"], phi, sc)
        tot += int((wv(cap["bits"], t) == cap["lev"]).sum()); n += len(t)
    print(f"{name:32s} match={tot/n:.4%}   implied loop = "
          f"{G*np.mean([v[1] for v in nuis.values()]):.1f} or "
          f"{G/np.mean([v[1] for v in nuis.values()]):.1f}")

# with the data-dependent w[] correction applied on the previous level
tot = n = 0
for cap in caps:
    key = f"{cap['pattern']}_{cap['rep']}"
    if key not in nuis:
        continue
    phi, sc, _ = nuis[key]
    lev = cap["lev"]
    prev = np.r_[0, lev[:-1]]
    t = phi + (cap["it"]*G + o[cap["slot"]] + w[cap["slot"]]*prev)*sc
    tot += int((wv(cap["bits"], t) == lev).sum()); n += len(t)
print(f"{'with w[] * previous level':32s} match={tot/n:.4%}")

print("\nper-capture scale stats:",
      np.round([v[1] for v in nuis.values()], 5)[:6],
      " mean", np.mean([v[1] for v in nuis.values()]))
print("effective loop period per capture (G*sc):",
      f"{G*np.mean([v[1] for v in nuis.values()]):.2f}")
print("NOTE their 'n' field:", [v[2] for v in list(nuis.values())[:5]])
