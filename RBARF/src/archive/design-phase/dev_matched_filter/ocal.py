"""Supervised calibration of the global slot offsets.

Force every bit to its true value, let the Viterbi find the phase track, then
re-fit the 8 slot offsets.  Iterate; report the consensus across captures.
"""
import sys, importlib.util, json
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)
meta, allc = load_dataset()


def sup_one(c, O0, rounds=6):
    s = linearize(c['capture'])
    lv, last = mf._grid(s)
    nloops = min(len(lv), (mf.NBITS + 1) // 2 + 1 + mf.TAIL_LOOPS)
    levels = [lv[i] for i in range(nloops)]
    truth = [int(b) for byte in bytes.fromhex(c['frame']) for b in f"{byte:08b}"]
    typ = list(truth)                          # every bit forced
    PSI = np.arange(mf.PSI_LO, mf.PSI_HI + 1e-9, mf.PSI_STEP)
    O = list(O0)
    best = None
    for P in np.arange(mf.P_LO, mf.P_HI + 1e-9, mf.P_STEP):
        E, tt = mf._emissions(levels, typ, nloops, P, PSI, O)
        r = mf._viterbi(E, tt, nloops, PSI, mf.JIT_LAM, mf.JIT_DEAD)
        if best is None or r[0] < best[0]:
            best = (r[0], r[1], r[2], P)
    cost, bits, psi, P = best
    for rnd in range(rounds):
        O = mf._refit_o(levels, truth, psi, P, O, nloops,
                        80.0 if rnd == 0 else 20.0, 4.0 if rnd == 0 else 1.0)
        bb = None
        for dP in (-1.5, -0.75, 0.0, 0.75, 1.5):
            E, tt = mf._emissions(levels, typ, nloops, P + dP, PSI, O)
            r = mf._viterbi(E, tt, nloops, PSI, mf.JIT_LAM, mf.JIT_DEAD)
            if bb is None or r[0] < bb[0]:
                bb = (r[0], r[1], r[2], P + dP)
        cost, bits, psi, P = bb
    return O, P, cost


if __name__ == '__main__':
    O0 = json.loads(sys.argv[1]) if len(sys.argv) > 1 else mf.SLOT_O
    rows = []
    for c in allc:
        if c['rep'] not in (0, 1):
            continue
        O, P, cost = sup_one(c, O0)
        rows.append(O)
        print(f"{c['pattern']:11s} r{c['rep']} P={P:7.2f} cost={cost:7.2f} "
              + ' '.join('%7.1f' % x for x in O), flush=True)
    A = np.array(rows)
    med = np.median(A, axis=0)
    print("median:", [round(float(x), 1) for x in med])
    print("mean  :", [round(float(x), 1) for x in A.mean(axis=0)])
    print("std   :", [round(float(x), 1) for x in A.std(axis=0)])
    print("JSON", json.dumps([round(float(x), 2) for x in med]))
