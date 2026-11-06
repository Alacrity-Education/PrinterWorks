"""Is the residual error a model bias or a genuine tie?

Compare the Viterbi cost of the decoder's own solution against the cost of
the SAME model with the true bits forced.  cost(free) << cost(truth) means
the model actively prefers the wrong answer (fixable by modelling);
cost(free) ~= cost(truth) means the evidence is a tie (need more signal).
"""
import sys, importlib.util
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)
meta, allc = load_dataset()


def run(c):
    s = linearize(c['capture'])
    lv, last = mf._grid(s)
    nloops = min(len(lv), (mf.NBITS + 1) // 2 + 1 + mf.TAIL_LOOPS)
    levels = [lv[i] for i in range(nloops)]
    truth = [int(b) for byte in bytes.fromhex(c['frame']) for b in f"{byte:08b}"]
    PSI = np.arange(mf.PSI_LO, mf.PSI_HI + 1e-9, mf.PSI_STEP)
    typ_free = mf._bit_types(meta)
    out = []
    for name, typ in (('free', typ_free), ('truth', list(truth))):
        best = None
        for P in np.arange(mf.P_LO, mf.P_HI + 1e-9, mf.P_STEP):
            E, tt = mf._emissions(levels, typ, nloops, P, PSI, mf.SLOT_O)
            r = mf._viterbi(E, tt, nloops, PSI, mf.JIT_LAM, mf.JIT_DEAD)
            if best is None or r[0] < best[0]:
                best = (r[0], r[1], P)
        out.append(best)
    err = sum(1 for k in range(32, 160) if out[0][1][k] != truth[k])
    return out[0][0], out[1][0], err, out[0][2], out[1][2]


tot_tie = tot_bias = 0
for c in allc:
    if c['rep'] not in (0, 1):
        continue
    cf, ct, err, pf, pt = run(c)
    tag = ''
    if err:
        if cf < ct - 1e-6:
            tag = 'BIAS'
            tot_bias += err
        else:
            tag = 'TIE'
            tot_tie += err
    print(f"{c['pattern']:11s} r{c['rep']} free={cf:7.3f}@{pf:.0f} truth={ct:7.3f}@{pt:.0f} "
          f"diff={ct-cf:7.3f} biterr={err:2d} {tag}", flush=True)
print(f"bit errors where model prefers wrong: {tot_bias}, ties: {tot_tie}")
