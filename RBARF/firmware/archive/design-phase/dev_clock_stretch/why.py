"""Inspect the C curve, anchors and per-bit sample phases for one capture."""
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
kmax = int(sys.argv[3]) if len(sys.argv) > 3 else 56
for c in caps:
    if c['pattern'] == pat and c['rep'] == rep:
        break
s = linearize(c['capture'])
fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
sc, llr, C, rate = cs._solve(s)
cyc = cs._cycles(s)

# per-bit sample phases
k = 0
i = 0
cells = [[] for _ in range(cs.NBITS)]
while i < len(s) and cyc[i] < C[0]:
    i += 1
while i < len(s) and k < cs.NBITS:
    if cyc[i] >= C[k + 1]:
        k += 1
        continue
    span = C[k + 1] - C[k]
    ph = (cyc[i] - C[k]) * cs.BIT / span
    cells[k].append((s[i][1], round(ph), s[i][2]))
    i += 1

print(f"{pat} rep{rep}  rate={rate}")
for kk in range(kmax):
    dec = 1 if llr[kk] > 0 else 0
    flag = '' if dec == fb[kk] else '  <<< WRONG'
    print(f"k={kk:3d} truth={fb[kk]} dec={dec} llr={llr[kk]:7.2f} "
          f"w={C[kk+1]-C[kk]:6.2f} cells={cells[kk]}{flag}")
