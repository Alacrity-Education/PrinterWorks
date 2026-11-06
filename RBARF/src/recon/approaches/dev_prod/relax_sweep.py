#!/usr/bin/env python3
"""RELAXATIONS A / B / C -- the empirical parameter search for v2.3.

Every bound the permissive decoder ships is picked here, from the
calibrated synthetic sampler, and reported old-vs-new.  Host only: no
bench, no simulator, no firmware.

modes
  probe   : window wide OPEN (K 1..65535, GATE_INFEAS 999, MK_TOL 48,
            A_MAX 11, T_MAX 131) over eps x t0 x payload x MALFORMATION
            class -- records the K each capture needs, the geometry
            counters, and whether the frame is still RECOVERABLE.  This
            is the measurement the A and B bounds are read off.
  gates   : the same grid decoded at a LADDER of candidate (K window,
            GATE_INFEAS, MK_TOL) settings -> delivery vs wrong-emission
            for each rung.
  chase   : A_MAX / A_PAIR / MG_PAIR / TIE_EMIT / T_MAX ladder at the
            chosen A+B point -> delivery, chase mix, wrong-emission.

Malformation classes are not decoration: MARGIN_INVESTIGATION.md SS4
measured that ~6 % of real frames mis-arm and refuse R1, and the fitted
arm phase spans 375-736 ns.  trunc/chop reproduce the two shapes (tail
missing / head missing) that an early or late arm produces.
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

ND = 48
EPS_PTS = [round(-0.08 + i * 0.005, 6) for i in range(33)]
T0_PTS = [375.0, 495.0, 616.0, 736.0]                # measured p10..p90
MALF = [("clean", 0, 0), ("tr8", 8, 0), ("tr16", 16, 0), ("tr24", 24, 0),
        ("tr40", 40, 0), ("ch2", 0, 2), ("ch4", 0, 4), ("ch8", 0, 8)]

WIDE = dict(K_MIN=1, K_MAX=65535, GATE_INFEAS=999, GATE_LABERR=999,
            MK_TOL=64, A_MAX=11, A_PAIR=11, MG_PAIR=8, TIE_EMIT=999,
            T_MAX=131, CHASE_SPLIT_VOTE=1)

_EV = None


def ev():
    global _EV
    if _EV is None:
        _EV = L.load_ref()
        _EV._configure(ND)
    return _EV


def one(args):
    name, data, eps, t0, mtag, tr, ch, params = args
    e = ev()
    e._configure(ND)
    L.set_params(e, **params)
    cap = L.capture(data, eps, t0, trunc=tr, chop=ch)
    try:
        out, info = e.decode_ex(L.linearize(cap))
    except AssertionError as exc:
        return dict(pat=name, eps=eps, t0=t0, malf=mtag, assertfail=str(exc)[:60],
                    path=None, cause="assert", K=0, delivered=False, wrong=False)
    return dict(
        pat=name, eps=eps, t0=t0, malf=mtag,
        path=info["path"], cause=info["cause"], K=info.get("K", 0),
        tau=info.get("tau", 0),
        viol=info.get("violations", 0), infeas=info.get("infeasible", 0),
        laberr=info.get("label_err", 0),
        nweak=info.get("n_weak", 0), ntied=info.get("n_tied", 0),
        trials=info.get("trials", 0), comps=info.get("comps", 0),
        nrefs=info.get("n_refs", 0), split=info.get("ref_split", 0),
        delivered=bool(out is not None and out == data),
        wrong=bool(out is not None and out != data))


def build_jobs(params):
    pats = L.prod_payloads()
    jobs = []
    for name, data in pats.items():
        for eps in EPS_PTS:
            for t0 in T0_PTS:
                for (mtag, tr, ch) in MALF:
                    jobs.append((name, data, eps, t0, mtag, tr, ch, params))
    return jobs


def run(jobs, nproc):
    with mp.Pool(nproc) as pool:
        return pool.map(one, jobs, chunksize=32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe", "gates", "chase"])
    ap.add_argument("-j", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.mode == "probe":
        rows = run(build_jobs(WIDE), a.j)
        out = a.out or str(SC / "relax_probe.jsonl.gz")
        with gzip.open(out, "wt") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print("probe: %d rows -> %s" % (len(rows), out))
    else:
        print("see relax_gates.py / relax_chase.py drivers")


if __name__ == "__main__":
    main()
