"""Per-slot mismatch profile: shift ONE slot's offset by delta and count
disagreements between the predicted wire level and the sample.  The
minimum locates the slot; the width of the flat basin bounds how well the
slot is identifiable at all."""
import sys
import numpy as np
from common import load_caps, fit_cap, sample_times, violation

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)
g = DOC.copy(); g[7] += 3.0
u = np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
DEL = np.arange(-500, 501, 5.0)

for rnd in range(ROUNDS):
    fits = {c.name: fit_cap(c, u)[:2] for c in caps}
    prof = np.zeros((8, len(DEL)))
    tot = np.zeros(8)
    for cap in caps:
        phi, P = fits[cap.name]
        t = sample_times(cap, phi, P, u)
        for s in range(8):
            m = cap.sl == s
            tot[s] += m.sum()
            for j, dl in enumerate(DEL):
                mm, _ = violation(cap, t[m] + dl, lev=cap.lev[m])
                prof[s, j] += mm.sum()
    corr = np.zeros(8)
    print(f"--- round {rnd}  u={np.round(u,5).tolist()}")
    for s in range(8):
        j = int(np.argmin(prof[s]))
        best = prof[s, j]
        flat = DEL[prof[s] <= best + 0.002 * tot[s]]
        corr[s] = DEL[j]
        print(f"  slot{s}: best delta={DEL[j]:+7.1f}ns  mism={best:5.0f}/{tot[s]:.0f}"
              f" ({best/tot[s]*100:5.2f}%)  basin[{flat.min():+.0f},{flat.max():+.0f}]"
              f"  mism@0={prof[s,len(DEL)//2]:5.0f} ({prof[s,len(DEL)//2]/tot[s]*100:5.2f}%)")
    Pbar = np.mean([f[1] for f in fits.values()])
    corr -= corr[0]
    u = u + corr / Pbar
    u = u - u[0]
print("final u:", np.round(u, 5).tolist())
print("gaps cycles (loop=40):", np.round(np.diff(np.append(u, 1.0)) * 40, 2))
print("offsets ns @2507.3:", np.round(u * 2507.3, 1))
