"""Global slot-fraction calibration using TRUE frame bits (offline only).

For each train capture: grid-fit (P, d, drift) then refit the 8 slot phases
(decoupled) against the true waveform; iterate.  Report the per-capture
fractions and their consensus -> global SLOT_FRAC constant.
"""
import sys, json, importlib.util
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)

BIT = mf.BIT


def fit_one(samples, frame_hex, frac0, rounds=8):
    m = mf._Model(samples, meta)
    bits = np.array([int(b) for byte in bytes.fromhex(frame_hex)
                     for b in f"{byte:08b}"] + [0] * mf.TAIL_CELLS, dtype=np.int64)
    # force all cells to truth so scoring == direct waveform match
    m.forced = bits.copy()
    m.free = np.zeros(m.ncell, dtype=bool)
    frac = np.array(frac0, dtype=np.float64)
    P0 = (191.4 * BIT) / m.a_last
    P, d, drift = P0, 60.0, 0.0
    sc, P, d = m.score_grid(np.arange(P0 - 14, P0 + 14.01, 0.4),
                            np.arange(-80, 260.01, 6.0), 0.0, frac)
    for r in range(rounds):
        bb = None
        for dr in np.arange(drift - 0.06, drift + 0.0601, 0.02):
            res = m.score_grid(np.arange(P - 1.2, P + 1.201, 0.05),
                               np.arange(d - 12, d + 12.01, 1.0), dr, frac)
            if bb is None or res[0] > bb[0]:
                bb = (res[0], res[1], res[2], float(dr))
        sc, P, d, drift = bb
        frac = mf._refit_slots(m, P, d, drift, bits, frac,
                               win=90.0 if r < 2 else 30.0,
                               step=6.0 if r < 2 else 1.0)
    t = m.times(P, d, drift, frac)
    good = m.full_score(t, bits)
    n = len(m.v)
    return frac, P, d, drift, good, n


meta, allc = load_dataset()
split = sys.argv[1] if len(sys.argv) > 1 else 'train'
sel = (0, 1) if split == 'train' else (0, 1, 2)
frac0 = json.loads(sys.argv[2]) if len(sys.argv) > 2 else mf.SLOT_FRAC
rows = []
G = N = 0
for c in allc:
    if c['rep'] not in sel:
        continue
    s = linearize(c['capture'])
    frac, P, d, dr, good, n = fit_one(s, c['frame'], frac0)
    rows.append(frac)
    G += good; N += n
    print(f"{c['pattern']:11s} r{c['rep']} P={P:7.2f} d={d:6.1f} dr={dr:+.3f} "
          f"miss={n-int(good):3d}/{n} frac*P=" +
          ' '.join('%6.1f' % (x * P) for x in frac), flush=True)
A = np.array(rows)
print("median frac:", np.round(np.median(A, axis=0), 5).tolist())
print("mean   frac:", np.round(A.mean(axis=0), 5).tolist())
print("std*2500  :", np.round(A.std(axis=0) * 2500, 1).tolist())
print(f"TOTAL match {G}/{N} = {G/N:.4%}")
print("MEDIAN_JSON", json.dumps([round(float(x), 6) for x in np.median(A, axis=0)]))
