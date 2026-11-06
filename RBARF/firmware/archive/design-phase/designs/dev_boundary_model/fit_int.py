"""Integer-cycle gap search: distribute the unaccounted cycles among the 8
inter-slot gaps of the documented [4,4,4,4,4,6,5,6] layout."""
import itertools, json, sys
import numpy as np
from common import load_caps, fit_cap, eval_all

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)   # gaps, sum 37
EXTRA = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def u_from_gaps(g):
    L = g.sum()
    return np.concatenate([[0.0], np.cumsum(g)[:-1] / L]), L


def evaluate(g):
    u, L = u_from_gaps(g)
    fits = {}
    for cap in caps:
        phi, P, v = fit_cap(cap, u)
        fits[cap.name] = (phi, P)
    v, m, n = eval_all(caps, u, fits)
    return v, m, n, fits


results = []
combos = [c for c in itertools.product(range(EXTRA + 1), repeat=8)
          if sum(c) == EXTRA]
print(f"{len(combos)} combos, extra={EXTRA}")
for c in combos:
    g = DOC + np.array(c, float)
    v, m, n, fits = evaluate(g)
    results.append((m, v, list(g), fits))
    print(f"g={[int(x) for x in g]} mism={m}/{n} ({m/n*100:.3f}%) viol={v:.0f}",
          flush=True)

results.sort(key=lambda r: r[0])
print("\nTOP 8 by mismatch count:")
for m, v, g, _ in results[:8]:
    print(f"  g={[int(x) for x in g]} mism={m} viol={v:.0f}")
best = results[0]
json.dump({"gaps": best[2], "mism": best[0], "viol": best[1],
           "fits": {k: list(x) for k, x in best[3].items()}},
          open(f"/home/alex.lucaci/Projects/RBARF/new-implementation/recon/"
               f"designs/dev_boundary_model/fitint{EXTRA}.json", "w"), indent=1)
