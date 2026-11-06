"""Oracle fit: what does the true C look like? (dev only, uses truth)."""
import sys, importlib.util
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location(
    'cs', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

meta, caps = load_dataset()
pat = sys.argv[1]
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 0
for c in caps:
    if c['pattern'] == pat and c['rep'] == rep:
        break
s = linearize(c['capture'])
fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
sc, llr, C, rate = cs._solve(s)
cyc = cs._cycles(s)
n_end = len(s)
for n in range(len(s) - 1, -1, -1):
    if s[n][2]:
        n_end = min(len(s), n + 12)
        break

# oracle: all bits known
cs.KNOWN = {k: fb[k] for k in range(cs.NBITS)}
Co, sco = cs._refine_ml(s, cyc, list(C), n_end)
# more knots for the oracle
cs._KNOTS = tuple(range(0, 193, 8))
Co, sco = cs._refine_ml(s, cyc, Co, n_end)
L0, L1, o = cs._cell_lls(s, cyc, Co, n_end)
bad = sum(1 for k in range(cs.NBITS) if (L1[k] > L0[k]) != bool(fb[k]))
print(f"oracle score={sco:.1f} bits-inconsistent={bad}")
print("k   C_est   C_oracle  diff(cyc)  diff(ns)  w_est  w_oracle")
for k in range(0, 100):
    d = C[k] - Co[k]
    print(f"{k:3d} {C[k]:9.2f} {Co[k]:9.2f} {d:8.2f} {d*62.5:9.1f} "
          f"{C[k+1]-C[k]:6.2f} {Co[k+1]-Co[k]:6.2f}")
