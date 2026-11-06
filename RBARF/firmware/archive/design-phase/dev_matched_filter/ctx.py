"""Show the local true-bit context of each decoding error."""
import sys, importlib.util
from collections import Counter
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)
meta, allc = load_dataset()

cnt = Counter()
tot = Counter()
rows = []
for c in allc:
    if c['rep'] not in (0, 1):
        continue
    s = linearize(c['capture'])
    got = mf.decode(s, meta) or b'\0' * 16
    fb = [int(b) for byte in bytes.fromhex(c['frame']) for b in f"{byte:08b}"]
    gb = fb[:32] + [int(b) for byte in got for b in f"{byte:08b}"] + fb[160:]
    for k in range(32, 160):
        ctx = ''.join(str(x) for x in fb[k - 2:k + 3])
        tot[ctx] += 1
        if fb[k] != gb[k]:
            cnt[ctx] += 1
            rows.append((c['pattern'], c['rep'], k, ctx, fb[k], gb[k], k % 2))
print("errors by 5-bit context (prev2 prev1 [bit] next1 next2):")
for ctx, n in cnt.most_common():
    print(f"  {ctx}  {n:3d} / {tot[ctx]:4d} = {n/tot[ctx]:.2%}")
print()
par = Counter(r[6] for r in rows)
print("errors by bit parity (cell within loop):", dict(par))
print("errors by true value:", Counter(r[4] for r in rows))
print("total errors", len(rows))
for r in rows[:60]:
    print("   ", r)
