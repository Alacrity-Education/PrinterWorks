"""Same dead-zone census but on an ORACLE per-loop time base.

The per-loop shift delta_i is chosen (using ground truth) to explain the
loop's 8 samples as well as possible.  This separates 'the decoder's
clock estimate is bad' from 'the sample really carries no information',
and gives the floor a perfectly clock-tracked decoder would hit.
"""
import numpy as np
from collections import Counter
from common import load_caps, fit_cap, sample_times

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)
import sys
G = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [4, 4, 4, 4, 4, 6, 5, 9]
g = np.array(G, float)
u = np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])
print("geometry cycles:", G, " u:", np.round(u, 5).tolist())
BIT, T0H, T1H, NB = 1250.0, 350.0, 700.0, 192
DEL = np.arange(-400, 401, 1.0)

hist = Counter(); noinfo_by_gap = Counter()
dec_err = dec_tot = noinfo = 0
err_by_ndec = Counter(); tot_by_ndec = Counter()
mism_tot = mism_n = 0
delta_stats = []
runs = Counter()
for cap in caps:
    phi, P = fit_cap(cap, u)[:2]
    t0 = sample_times(cap, phi, P, u)
    it = cap.it.astype(int); E = cap.E
    t = t0.copy()
    ds = []
    for i in range(int(it.max()) + 1):
        m = it == i
        tt = t0[m][:, None] + DEL[None, :]
        pred = np.searchsorted(E, tt.ravel(), side="right").reshape(tt.shape) & 1
        mism = (pred != cap.lev[m][:, None]).sum(0)
        j = int(np.argmin(mism))
        t[m] = t0[m] + DEL[j]
        if i < 100:
            mism_tot += int(mism[j]); mism_n += int(m.sum()); ds.append(DEL[j])
    delta_stats.append((np.min(ds), np.max(ds), np.std(np.diff(ds))))
    o = np.argsort(t); tt = t[o]; lv = cap.lev[o]; sl = cap.sl[o]
    bits = np.array(cap.bits)
    blind = np.zeros(NB, bool)
    for k in range(NB):
        a = k * BIT
        m = (tt >= a) & (tt < a + BIT)
        tau = tt[m] - a
        d = (tau >= T0H) & (tau < T1H)
        nd = int(d.sum()); hist[nd] += 1
        if nd == 0:
            noinfo += 1; blind[k] = True
            j = np.searchsorted(tt, a + T0H)
            if 0 < j < len(tt):
                noinfo_by_gap[int(sl[j - 1])] += 1
        else:
            call = 1 if lv[m][d].mean() >= 0.5 else 0
            dec_tot += 1; tot_by_ndec[nd] += 1
            if call != bits[k]:
                dec_err += 1; err_by_ndec[nd] += 1
    r = 0
    for k in range(NB):
        if blind[k]: r += 1
        else:
            if r: runs[r] += 1
            r = 0
    if r: runs[r] += 1

n = sum(hist.values())
print(f"oracle per-loop sample mismatch: {mism_tot}/{mism_n} ({mism_tot/mism_n*100:.3f}%)")
d = np.array(delta_stats)
print(f"per-loop shift: range median={np.median(d[:,1]-d[:,0]):.0f}ns "
      f"max={np.max(d[:,1]-d[:,0]):.0f}ns  |step| sd median={np.median(d[:,2]):.1f}ns")
print("decisive samples per cell:", {k: f"{v} ({v/n*100:.2f}%)" for k, v in sorted(hist.items())})
print(f"blind cells: {noinfo}/{n} ({noinfo/n*100:.2f}%)  by gap: {dict(sorted(noinfo_by_gap.items()))}")
print(f"decisive-only error: {dec_err}/{dec_tot} ({dec_err/dec_tot*100:.3f}%)")
for k in sorted(tot_by_ndec):
    print(f"   ndec={k}: err {err_by_ndec[k]}/{tot_by_ndec[k]} "
          f"({err_by_ndec[k]/tot_by_ndec[k]*100:.3f}%)")
print("blind-run lengths:", dict(sorted(runs.items())))
