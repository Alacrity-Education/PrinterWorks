#!/usr/bin/env python3
"""RELAXATION ladder: delivery vs WRONG-EMISSION at each candidate bound.

Grid: 27 production payloads (the 10 drive_prod gate frames + all 17
Klipper macro frames, which are the long-zero-run shapes that produced
the project's only two wrong emissions -- PROD_CLOSURE SS11.4) x an eps
sweep x the MEASURED arm-phase spread, decoded by the v2.3 reference at
each parameter rung.  Host only.
"""
import argparse
import gzip
import json
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import v23lib as L                                              # noqa: E402

KL = json.load(open(SC.parents[2] / "klipper" /
                    "bench_klipper_macro_results.prefix_baseline.json"))


def payloads():
    p = dict(L.prod_payloads())
    for r in KL["rows"]:
        fr = bytes.fromhex(r["frame"])
        if len(fr) == 60:
            p.setdefault("kl_" + r["case"], fr[4:52])
    return p


PAY = payloads()

# parameter rungs.  base = every gate at its v2.3 candidate value; the
# named rungs move ONE bound so the yield of each is attributable.
BASE = dict(K_MIN=40000, K_MAX=64000, GATE_INFEAS=24, MK_TOL=12,
            A_MAX=11, A_PAIR=11, MG_PAIR=8, TIE_EMIT=11, T_MAX=131,
            CHASE_SPLIT_VOTE=1)
RUNGS = {
    "v22gates":  dict(BASE, K_MIN=46000, K_MAX=60000, GATE_INFEAS=4,
                      MK_TOL=0, A_MAX=5, A_PAIR=3, MG_PAIR=4, TIE_EMIT=8,
                      T_MAX=16, CHASE_SPLIT_VOTE=0),
    "A_only":    dict(BASE, MK_TOL=0, A_MAX=5, A_PAIR=3, MG_PAIR=4,
                      TIE_EMIT=8, T_MAX=16, CHASE_SPLIT_VOTE=0),
    "AB":        dict(BASE, A_MAX=5, A_PAIR=3, MG_PAIR=4, TIE_EMIT=8,
                      T_MAX=16, CHASE_SPLIT_VOTE=0),
    "ABC_tie8":  dict(BASE, TIE_EMIT=8),
    "ABC":       dict(BASE),
    "tie16":     dict(BASE, TIE_EMIT=16),
    "tie32":     dict(BASE, TIE_EMIT=32),
    "tie64":     dict(BASE, TIE_EMIT=64),
    "tie_off":   dict(BASE, TIE_EMIT=100000),
    "amax16":    dict(BASE, A_MAX=16, A_PAIR=16, TIE_EMIT=100000),
    "pairW22":   dict(BASE, A_PAIR=3, MG_PAIR=4, TIE_EMIT=100000),
    "noSplit":   dict(BASE, CHASE_SPLIT_VOTE=0, TIE_EMIT=100000),
    "T16":       dict(BASE, T_MAX=16, TIE_EMIT=100000),
    "T67":       dict(BASE, T_MAX=67, TIE_EMIT=100000),
}

_EV = None
_ND = 48


def ev():
    global _EV
    if _EV is None:
        _EV = L.load_ref()
    return _EV


def one(job):
    rung, name, eps, t0 = job
    data = PAY[name]
    e = ev()
    e._configure(_ND)
    L.set_params(e, **RUNGS[rung])
    cap = L.capture(data, eps, t0)
    try:
        out, info = e.decode_ex(L.linearize(cap))
    except AssertionError:
        return (rung, name, eps, t0, "assert", 0, 0, 0, 0, 0, 0, 0, 0, 0)
    return (rung, name, eps, t0,
            info["cause"] or ("ok" if out == data else "WRONG"),
            int(out is not None), int(out is not None and out == data),
            info.get("n_weak", 0), info.get("n_tied", 0),
            info.get("trials", 0), info.get("comps", 0),
            info.get("n_refs", 0), info.get("violations", 0),
            info.get("infeasible", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps-step", type=float, default=0.002)
    ap.add_argument("--eps-max", type=float, default=0.08)
    ap.add_argument("--t0", type=int, default=4)
    ap.add_argument("--rungs", default="")
    ap.add_argument("-j", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--out", default=str(SC / "relax_ladder.jsonl.gz"))
    a = ap.parse_args()
    n = int(round(2 * a.eps_max / a.eps_step)) + 1
    eps_pts = [round(-a.eps_max + i * a.eps_step, 6) for i in range(n)]
    t0_pts = [375.0 + i * (736.0 - 375.0) / max(1, a.t0 - 1)
              for i in range(a.t0)]
    rungs = a.rungs.split(",") if a.rungs else list(RUNGS)
    jobs = [(r, nm, e, t) for r in rungs for nm in PAY
            for e in eps_pts for t in t0_pts]
    print("rungs=%d payloads=%d eps=%d t0=%d -> %d decodes"
          % (len(rungs), len(PAY), len(eps_pts), len(t0_pts), len(jobs)))
    with mp.Pool(a.j) as pool:
        rows = pool.map(one, jobs, chunksize=64)
    with gzip.open(a.out, "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
