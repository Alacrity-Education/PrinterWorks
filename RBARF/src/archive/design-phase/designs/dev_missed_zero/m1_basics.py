"""Basic facts: frame extent, samples/bit, swallowed 0 count, merged pulses."""
from mz_common import *
from collections import Counter
import numpy as np

meta, caps = load()
tot = Counter()
per = []
for c in caps:
    P = prepare(c)
    t, lv, bits = P["t"], P["lv"], P["bits"]
    infr = (t >= -100) & (t < NBITS * BIT + 200)
    nsamp = int(infr.sum())
    # per-bit high-sample count
    k = np.floor(t / BIT).astype(np.int64)
    inhi = wire_levels(t, bits)          # true wire level at sample time
    cnt_hi = np.zeros(NBITS, int)
    for m in np.nonzero(infr & inhi)[0]:
        if 0 <= k[m] < NBITS:
            cnt_hi[k[m]] += 1
    b = np.array(bits)
    sw0 = int(((b == 0) & (cnt_hi == 0)).sum())
    sw1 = int(((b == 1) & (cnt_hi == 0)).sum())
    n0 = int((b == 0).sum()); n1 = int((b == 1).sum())
    # observed high runs inside frame
    runs = [r for r in pulse_runs(lv) if t[r[0]] < NBITS * BIT + 200]
    # agreement inside frame
    pred = wire_levels(t, bits, H1M, H0M)
    ag = int((pred[infr] == lv[infr]).sum())
    per.append((c["pattern"], c["rep"], nsamp, n1, n0, sw0, sw1, len(runs), ag))
    tot["nsamp"] += nsamp; tot["sw0"] += sw0; tot["sw1"] += sw1
    tot["n0"] += n0; tot["n1"] += n1; tot["runs"] += len(runs)
    tot["ag"] += ag
    tot["hi0"] += int(cnt_hi[b == 0].sum()); tot["hi1"] += int(cnt_hi[b == 1].sum())

print(f"{'pat':11s} rep nsamp_in_frame n1 n0 swallowed0 lost1 pulses agree%")
for r in per:
    print(f"{r[0]:11s} {r[1]}  {r[2]:5d} {r[3]:4d} {r[4]:4d}  {r[5]:4d} {r[6]:4d}  {r[7]:4d}  {100*r[8]/r[2]:6.2f}")
print()
print("total in-frame samples", tot["nsamp"], "-> samples/bit", tot["nsamp"] / (54 * NBITS))
print("swallowed 0-bits", tot["sw0"], "/", tot["n0"], "=", tot["sw0"] / tot["n0"])
print("lost 1-bits", tot["sw1"], "/", tot["n1"])
print("mean high samples per 0-bit", tot["hi0"] / tot["n0"], " per 1-bit", tot["hi1"] / tot["n1"])
print("visible pulses", tot["runs"], " vs non-swallowed bits", tot["n0"] + tot["n1"] - tot["sw0"] - tot["sw1"])
print("in-frame sample agreement", tot["ag"] / tot["nsamp"])
