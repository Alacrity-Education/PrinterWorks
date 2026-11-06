import numpy as np, json
from exp26_loopperiod_showdown import CS, N, best_cap, O_CAL_FRAC, O_DOC_FRAC, H1, H0
for tag, of in (("cal-o", O_CAL_FRAC), ("doc-o", O_DOC_FRAC)):
    print(f"== {tag} ==")
    for Leff in np.arange(2492., 2513., 2.0):
        tot = sum(best_cap(c, Leff, of, H1, H0) for c in CS)
        print(f"  Leff={Leff:8.1f}  {tot/N:.4%}")
