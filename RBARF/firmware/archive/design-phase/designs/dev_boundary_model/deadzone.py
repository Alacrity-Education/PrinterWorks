"""Where is information genuinely absent?

Within a bit cell [k*1250, (k+1)*1250) the wire is HIGH on [0,350) for
both bit values, HIGH on [350,700) only if the bit is 1, and LOW on
[700,1250) for both.  So only samples whose in-cell time falls in the
DECISIVE window [350,700) (350 ns wide, 28% of the cell) carry the bit.
This measures, on the real captures, how many decisive samples each cell
gets, which slot gaps eat the window, and how often the naive
decisive-only decision is right.
"""
import numpy as np
from collections import Counter
from common import load_caps, fit_cap, sample_times

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)
g = DOC.copy(); g[7] += 3.0
u = np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])
BIT, T0H, T1H = 1250.0, 350.0, 700.0
NB = 192

hist = Counter()
dec_err = 0; dec_tot = 0
noinfo = 0
noinfo_by_gap = Counter()
gap_hist = Counter()
margin = []
per_cap = {}
runs_all = []
for cap in caps:
    phi, P = fit_cap(cap, u)[:2]
    t = sample_times(cap, phi, P, u)
    o = np.argsort(t); t = t[o]; lv = cap.lev[o]; sl = cap.sl[o]
    bits = np.array(cap.bits)
    ndec_cell = np.zeros(NB, int)
    wrong = 0
    for k in range(NB):
        a, b = k * BIT, (k + 1) * BIT
        m = (t >= a) & (t < b)
        tau = t[m] - a
        d = (tau >= T0H) & (tau < T1H)
        ndec_cell[k] = d.sum()
        hist[int(d.sum())] += 1
        if d.sum() == 0:
            noinfo += 1
            # which inter-sample gap covers the decisive window?
            j = np.searchsorted(t, a + T0H)
            if 0 < j < len(t):
                noinfo_by_gap[int(sl[j - 1])] += 1
        else:
            votes = lv[m][d]
            call = 1 if votes.mean() >= 0.5 else 0
            dec_tot += 1
            if call != bits[k]:
                dec_err += 1; wrong += 1
        # margin of each decisive sample to the window edges
        for x in tau[d]:
            margin.append(min(x - T0H, T1H - x))
    # run lengths of consecutive cells with no decisive sample
    r = 0
    for k in range(NB):
        if ndec_cell[k] == 0:
            r += 1
        else:
            if r: runs_all.append(r)
            r = 0
    if r: runs_all.append(r)
    per_cap[cap.name] = (int((ndec_cell == 0).sum()), wrong)

n = sum(hist.values())
print("decisive samples per bit cell:",
      {k: f"{v} ({v/n*100:.2f}%)" for k, v in sorted(hist.items())})
print(f"cells with NO decisive sample: {noinfo}/{n} ({noinfo/n*100:.2f}%)")
print("  by inter-sample gap index (slot s -> s+1):",
      dict(sorted(noinfo_by_gap.items())))
print(f"decisive-only decision error: {dec_err}/{dec_tot} ({dec_err/dec_tot*100:.3f}%)")
m = np.array(margin)
print(f"decisive-sample margin to window edge: median={np.median(m):.0f}ns "
      f"p10={np.percentile(m,10):.0f} p05={np.percentile(m,5):.0f} "
      f"frac<30ns={(m<30).mean()*100:.1f}%")
rr = Counter(runs_all)
print("run lengths of consecutive info-less cells:", dict(sorted(rr.items())))
print("worst captures (blind cells, decisive errors):",
      sorted(per_cap.items(), key=lambda kv: -kv[1][0])[:8])
