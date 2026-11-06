"""Print per-slot level vs iteration in a periodic payload region."""
import sys
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

meta, allc = load_dataset()
pat = sys.argv[1] if len(sys.argv) > 1 else 'zeros'
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 0
i0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
i1 = int(sys.argv[4]) if len(sys.argv) > 4 else 100
for c in allc:
    if c['pattern'] == pat and c['rep'] == rep:
        s = linearize(c['capture'])
        grid = {}
        for it, sl, v in s:
            grid[(it, sl)] = v
        print(f"{pat} r{rep}  payload {c['payload']}")
        print('iter  ' + ''.join(f"{k}" for k in range(8)))
        for i in range(i0, i1):
            row = ''.join(str(grid.get((i, k), '?')) for k in range(8))
            print(f"{i:4d}  {row}")
        break
