"""Fine scan of the shared L around the exp17 peak, more alternation rounds."""
import numpy as np
from exp17_identify_L import prep, evaluate
from common import load_all

meta, caps = load_all()
cs = prep(caps)
N = sum(len(c["lev"]) for c in cs)
o0 = np.array([0., 250., 500., 750., 1000., 1250., 1625., 1937.5])
best = None
for L in np.arange(2494.0, 2504.5, 0.5):
    tot, o, phi = evaluate(cs, L, o0, rounds=6)
    print(f"L={L:8.2f} match={tot:6d} {tot/N:8.4%} o={np.round(o,1).tolist()}")
    if best is None or tot > best[0]:
        best = (tot, L, o)
print(f"\nBEST L={best[1]:.2f} match={best[0]/N:.4%}")
print(f"o = {np.round(best[2],1).tolist()}")
print(f"gaps(ns) = {np.round(np.diff(np.append(best[2], best[1]+best[2][0])),1).tolist()}")
print(f"o in cycles of L/40 = {np.round(best[2]/(best[1]/40.),2).tolist()}")
