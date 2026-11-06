"""Do falling edges become useful once they get their OWN global per-slot
bias (and separate biases for T0H-falls vs T1H-falls)?"""
import numpy as np
from common import load_all, BIT_NS
from exp8_pipeline import A, BIAS_F, coarse, refine
T0H, T1H = 350.0, 700.0

meta, caps = load_all()
LG = np.arange(2300., 2705., 2.)
base = []
for cap in caps:
    Lc, J, _ = coarse(cap, LG)
    phi, L, res, k, umid, s0 = refine(cap, Lc)
    base.append((phi, L))

# collect falling-edge residuals grouped by (slot, bitvalue)
bF = np.zeros((2, 8))
for it in range(6):
    acc = [[[] for _ in range(8)] for _ in range(2)]
    for cap, (phi, L) in zip(caps, base):
        lev = cap["lev"]; d = np.diff(lev.astype(int))
        idx = np.nonzero(d < 0)[0]
        u = cap["it"] + A[cap["slot"]]
        umid = .5*(u[idx]+u[idx+1]); s0 = cap["slot"][idx]
        rt = np.arange(192)*BIT_NS
        ft = rt + np.where(cap["bits"] == 1, T1H, T0H)
        bv = cap["bits"]
        t = phi + umid*L + bF[0, s0]*0  # placeholder
        t = phi + umid*L
        for j in range(len(t)):
            m = int(np.argmin(np.abs(ft - t[j])))
            e = ft[m] - t[j] - bF[bv[m], s0[j]]
            if abs(e) < .45*BIT_NS:
                acc[bv[m]][s0[j]].append(e)
    bF = bF + np.array([[np.median(v) if v else 0. for v in row] for row in acc])
    rms = np.sqrt(np.mean([e**2 for row in acc for v in row for e in v]))
    print(f"it{it}: rms={rms:6.1f}  bF0={np.round(bF[0],0).tolist()}  "
          f"bF1={np.round(bF[1],0).tolist()}")
print("\nfall bias for 0-bits (ns):", np.round(bF[0],1).tolist())
print("fall bias for 1-bits (ns):", np.round(bF[1],1).tolist())
print("rise bias (ns):           ", np.round(BIF := BIAS_F*2499.6,1).tolist())
