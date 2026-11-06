#!/usr/bin/env python3
"""Pin the RELAXATION A/B bounds with evidence: one bound moved per rung,
over the plateau + fast-side + full-envelope eps grids x 27 payloads x the
12 measured arm phases.  Reports delivery AND wrong emissions per rung."""
import collections
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import v23lib as L                                              # noqa: E402
from relax_ladder import PAY                                    # noqa: E402

# NOTE: every rung must carry EVERY key it or any sibling touches --
# the worker reuses one module instance, and _configure() only resets the
# version-dependent constants, so a key set by one rung would leak into
# the next.  GATE_LABERR is in BASE for exactly that reason.
BASE = dict(K_MIN=40000, K_MAX=64000, GATE_INFEAS=24, MK_TOL=12, A_MAX=11,
            A_PAIR=11, MG_PAIR=8, TIE_EMIT=100000, T_MAX=131,
            CHASE_SPLIT_VOTE=1, GATE_LABERR=6)
RUNGS = {
    "final":      dict(BASE),
    "infeas4":    dict(BASE, GATE_INFEAS=4),
    "infeas8":    dict(BASE, GATE_INFEAS=8),
    "infeas_off": dict(BASE, GATE_INFEAS=100000),
    "mk0":        dict(BASE, MK_TOL=0),
    "mk4":        dict(BASE, MK_TOL=4),
    "mk8":        dict(BASE, MK_TOL=8),
    "mk_off":     dict(BASE, MK_TOL=64),
    "both_off":   dict(BASE, GATE_INFEAS=100000, MK_TOL=64),
    "laberr_off": dict(BASE, GATE_LABERR=100000),
    "Kv22":       dict(BASE, K_MIN=46000, K_MAX=60000),
    "Kwide":      dict(BASE, K_MIN=1, K_MAX=65535),
}
T0 = [375.0 + i * (736.0 - 375.0) / 11 for i in range(12)]
EPS = ([round(-0.025 + i * 0.0005, 6) for i in range(53)] +
       [round(i * 0.0005, 6) for i in range(61)] +
       [round(-0.08 + i * 0.004, 6) for i in range(41)])
_EV = None


def one(job):
    rung, nm, eps, t0 = job
    global _EV
    if _EV is None:
        _EV = L.load_ref()
    e = _EV
    e._configure(48)
    L.set_params(e, **RUNGS[rung])
    try:
        out, info = e.decode_ex(L.linearize(L.capture(PAY[nm], eps, t0)))
    except AssertionError:
        return (rung, "assert", 0, 0)
    em = out is not None
    ok = em and out == PAY[nm]
    return (rung, info["cause"] or ("ok" if ok else "WRONG"), int(em), int(ok))


def main():
    jobs = [(r, nm, e, t) for r in RUNGS for nm in PAY for e in EPS for t in T0]
    print(len(jobs), "decodes")
    with mp.Pool(23) as p:
        rows = p.map(one, jobs, chunksize=128)
    agg = collections.defaultdict(lambda: [0, 0, 0])
    cz = collections.defaultdict(collections.Counter)
    for r in rows:
        agg[r[0]][0] += 1
        agg[r[0]][1] += r[2]
        agg[r[0]][2] += r[2] - r[3]
        cz[r[0]][r[1]] += 1
    print("%-11s %8s %9s %7s %9s  %s" %
          ("rung", "decodes", "emitted", "WRONG", "wrong%", "top causes"))
    for k in RUNGS:
        n, em, wr = agg[k]
        print("%-11s %8d %9d %7d %8.4f%%  %s" %
              (k, n, em, wr, 100.0 * wr / em if em else 0,
               ", ".join("%s=%d" % x for x in cz[k].most_common(4))))


if __name__ == "__main__":
    main()
