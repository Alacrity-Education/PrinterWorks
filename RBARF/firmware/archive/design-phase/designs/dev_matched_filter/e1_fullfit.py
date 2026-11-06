"""E1: how well does an affine time model (b,k) + fixed slot layout explain
the WHOLE frame?  Ground truth used for analysis only."""
import numpy as np
from mfn import *

meta, caps = load()
LAYOUTS = {"doc37": LAY_DOC * (2507.3 / 37.0) / CY * 1.0,
           "end3": LAY_END3, "stage3": LAY_S3}
LAYOUTS["doc37"] = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) * (2507.3 / 37.0) / CY


def fit(tau, lv, bits, brng=(-300., 800.), krng=(0.99, 1.02),
        nb=101, nk=101, iters=8, tmax=245000.):
    b0, b1 = brng
    k0, k1 = krng
    for _ in range(iters):
        bs = np.linspace(b0, b1, nb)
        ks = np.linspace(k0, k1, nk)
        # x[b,k,j]
        X = bs[:, None, None] + ks[None, :, None] * tau[None, None, :]
        M = (X >= -600) & (X <= tmax)
        pred = level_at(bits, X.ravel()).reshape(X.shape)
        agree = ((pred == lv[None, None, :]) & M).sum(2)
        n = M.sum(2)
        i, j = np.unravel_index(np.argmax(agree), agree.shape)
        bb, kk = bs[i], ks[j]
        db = (b1 - b0) / (nb - 1)
        dk = (k1 - k0) / (nk - 1)
        b0, b1 = bb - db, bb + db
        k0, k1 = kk - dk, kk + dk
    return int(agree[i, j]), int(n[i, j]), bb, kk


for name, lay in LAYOUTS.items():
    ta = tn = 0
    ks = []
    rows = []
    for cap in caps:
        sm = linearize(cap["capture"])
        tau, lv, it, sl = tau_array(sm, lay)
        bits = bits_of(bytes.fromhex(cap["payload"]))
        a, n, b, k = fit(tau, lv, bits)
        ta += a; tn += n; ks.append(k)
        rows.append((cap["pattern"], cap["rep"], n - a, n, b, k))
    print(f"{name:8s} mismatch={tn-ta}/{tn} ({(tn-ta)/tn*100:.3f}%)  "
          f"loop_ns {min(ks)*2500:.2f}..{max(ks)*2500:.2f}")
    if name == "end3":
        keep = rows
print("\nper-capture (end3):")
for p, r, mm, n, b, k in keep:
    print(f"  {p:11s} rep{r} mism={mm:4d}/{n} b={b:8.1f} loop={k*2500:8.2f}ns")
