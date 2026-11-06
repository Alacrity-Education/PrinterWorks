"""Is the loop period a function of the sampled levels?

Build an oracle time map (truth-seeded), then regress each loop's duration
and each inter-slot gap on the observed levels.
"""
import sys, importlib.util
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location(
    'cs', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)
BIT = cs.BIT


def oracle_times(c):
    s = linearize(c['capture'])
    fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
    sc, llr, C, rate = cs._solve(s)
    cyc = cs._cycles(s)
    n_end = len(s)
    for n in range(len(s) - 1, -1, -1):
        if s[n][2]:
            n_end = min(len(s), n + 12)
            break
    saveknots = cs._KNOTS
    saveknown = cs.KNOWN
    cs.KNOWN = {k: fb[k] for k in range(cs.NBITS)}
    C, _ = cs._refine_ml(s, cyc, list(C), n_end)
    cs._KNOTS = tuple(range(0, 193, 4))
    C, _ = cs._refine_ml(s, cyc, C, n_end)
    L0, L1, o = cs._cell_lls(s, cyc, C, n_end)
    bad = sum(1 for k in range(cs.NBITS) if (L1[k] > L0[k]) != bool(fb[k]))
    cs._KNOTS = saveknots
    cs.KNOWN = saveknown
    # times
    times = {}
    k = 0
    i = 0
    while i < n_end and cyc[i] < C[0]:
        i += 1
    while i < n_end and k < cs.NBITS:
        if cyc[i] >= C[k + 1]:
            k += 1
            continue
        w = C[k + 1] - C[k]
        times[(s[i][0], s[i][1])] = k * BIT + (cyc[i] - C[k]) * BIT / w
        i += 1
    lev = {(it, sl): v for it, sl, v in s}
    return times, lev, bad


def main():
    meta, caps = load_dataset()
    rows = []
    for c in caps:
        if c['rep'] == 2:
            continue
        times, lev, bad = oracle_times(c)
        if bad > 4:
            print(f"skip {c['pattern']}{c['rep']} bad={bad}")
            continue
        its = sorted({it for it, sl in times})
        for it in its:
            if all((it, sl) in times for sl in range(8)) and (it + 1, 0) in times:
                D = times[(it + 1, 0)] - times[(it, 0)]
                nh = sum(lev[(it, sl)] for sl in range(8))
                gaps = [times[(it, sl + 1)] - times[(it, sl)] for sl in range(7)]
                gaps.append(times[(it + 1, 0)] - times[(it, 7)])
                rows.append((D, nh, [lev[(it, sl)] for sl in range(8)], gaps,
                             c['pattern'], c['rep'], it))
        print(f"{c['pattern']:11s}{c['rep']} bad={bad} n={len(its)}", flush=True)
    print("total loops", len(rows))
    # loop duration vs number of high samples
    for nh in range(9):
        v = sorted(r[0] for r in rows if r[1] == nh)
        if len(v) > 4:
            print(f"nhigh={nh}: n={len(v):4d} median D={v[len(v)//2]:8.1f} "
                  f"p10={v[len(v)//10]:7.1f} p90={v[9*len(v)//10]:7.1f}")
    # gap vs level of the sample that starts it
    print("gap[s] by level of sample s:")
    for s_ in range(8):
        for L in (0, 1):
            v = sorted(r[3][s_] for r in rows if r[2][s_] == L)
            if len(v) > 4:
                print(f"  slot {s_} lev {L}: n={len(v):4d} med={v[len(v)//2]:7.1f}")


main()
