from common import *
meta, caps = load()
print(f"{'pat':11s} {'rep':>3s} {'agree':>6s}/{'n':<5s} {'loop_ns':>9s} {'t0':>7s}")
res=[]
for c in caps:
    p = prepare(c)
    res.append(p)
    print(f"{c['pattern']:11s} {c['rep']:3d} {p['agree']:6d}/{p['n']:<5d} "
          f"{p['scale']*LOOP_NOM:9.2f} {p['t0']:7.1f}")
import statistics
print("loop_ns median", statistics.median(p['scale']*LOOP_NOM for p in res))
print("mismatch rate", 1-sum(p['agree'] for p in res)/sum(p['n'] for p in res))
