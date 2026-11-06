"""Measure the transmitter's T0H / T1H from the captures themselves.

harness.py hard-codes 350/700 ns; the task brief says 375/750.  Scan both
as free parameters and score the fitted model."""
import numpy as np
from common import load_caps, fit_cap, sample_times, BIT
import common

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)
g = DOC.copy(); g[7] += 3.0
u = np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])


def edges_with(bits, h0, h1):
    E = []
    for k, b in enumerate(bits):
        E.append(k * BIT)
        E.append(k * BIT + (h1 if b else h0))
    return np.array(E)


best = None
for h0 in np.arange(300, 451, 12.5):
    for h1 in np.arange(650, 826, 12.5):
        tot = n = 0
        for cap in caps:
            cap.E = edges_with(cap.bits, h0, h1)
            phi, P = fit_cap(cap, u)[:2]
            t = sample_times(cap, phi, P, u)
            idx = np.searchsorted(cap.E, t, side="right")
            pred = idx & 1
            keep = (t > -400) & (t < cap.E[-1] + 400)
            tot += int(((pred != cap.lev) & keep).sum()); n += int(keep.sum())
        if best is None or tot < best[0]:
            best = (tot, h0, h1, n)
        print(f"h0={h0:6.1f} h1={h1:6.1f}  mism={tot}/{n} ({tot/n*100:.3f}%)",
              flush=True)
print("BEST:", best, f"{best[0]/best[3]*100:.3f}%")
