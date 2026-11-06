#!/usr/bin/env python3
"""THE WRONG-EMISSION MEASUREMENT for v2.3 (host, synthetic, no bench).

The v2.3 directive is "almost always emit", with the wrong-emission rate
held at <= 0.2 % of EMISSIONS and reported honestly at every step.  This
script is that report's numerator and denominator.

Corpus (production geometry, 48 DATA bytes, 60-byte frames):
  S1 plateau  eps -2.5 .. +0.1 % at 0.05 %   -- where deliveries live
  S2 envelope eps -8 .. +8 % at 0.2 %        -- the whole HSI envelope
  S3 fastside eps 0 .. +3 % at 0.05 %        -- where BOTH recorded
                                                catastrophics happened
  S4 replay   the two PROD_CLOSURE SS11.4 frames, eps +0.10..+0.40 %
              at 0.01 %, all 12 arm phases   -- the catastrophic replay
each x 27 payloads (10 drive_prod gate + 17 Klipper macro frames, the
long-zero-run shapes that produced the two wrong emissions) x 12 arm
phases over the MEASURED 375-736 ns spread.
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import v23lib as L                                              # noqa: E402
from relax_ladder import PAY                                    # noqa: E402

T0 = [375.0 + i * (736.0 - 375.0) / 11 for i in range(12)]
CAT = ("kl_preset_rain", "kl_preset_rain_rev")

RUNGS = {
    "tie11":   dict(K_MIN=40000, K_MAX=64000, GATE_INFEAS=24, MK_TOL=12,
                    A_MAX=11, A_PAIR=11, MG_PAIR=8, TIE_EMIT=11,
                    T_MAX=131, CHASE_SPLIT_VOTE=1),
    "tieoff":  dict(K_MIN=40000, K_MAX=64000, GATE_INFEAS=24, MK_TOL=12,
                    A_MAX=11, A_PAIR=11, MG_PAIR=8, TIE_EMIT=100000,
                    T_MAX=131, CHASE_SPLIT_VOTE=1),
    "v22":     dict(K_MIN=46000, K_MAX=60000, GATE_INFEAS=4, MK_TOL=0,
                    A_MAX=5, A_PAIR=3, MG_PAIR=4, TIE_EMIT=8,
                    T_MAX=16, CHASE_SPLIT_VOTE=0),
}


def grid(name):
    if name == "S1":
        return [round(-0.025 + i * 0.0005, 6) for i in range(53)], list(PAY)
    if name == "S2":
        return [round(-0.08 + i * 0.002, 6) for i in range(81)], list(PAY)
    if name == "S3":
        return [round(0.0 + i * 0.0005, 6) for i in range(61)], list(PAY)
    if name == "S4":
        return [round(0.0010 + i * 0.0001, 6) for i in range(31)], list(CAT)
    raise ValueError(name)


_EV = None


def one(job):
    rung, set_, name, eps, t0 = job
    data = PAY[name]
    global _EV
    if _EV is None:
        _EV = L.load_ref()
    e = _EV
    e._configure(48)
    L.set_params(e, **RUNGS[rung])
    cap = L.capture(data, eps, t0)
    try:
        out, info = e.decode_ex(L.linearize(cap))
    except AssertionError as exc:
        return (rung, set_, name, eps, t0, "assert", 0, 0, 0, 0, 0, 0, 0,
                str(exc)[:40])
    emit = out is not None
    ok = emit and out == data
    return (rung, set_, name, eps, t0, info["cause"] or ("ok" if ok
            else "WRONG"), int(emit), int(ok), info.get("path") == "chase",
            info.get("trials", 0), info.get("comps", 0),
            info.get("n_refs", 0), info.get("n_tied", 0),
            out.hex() if (emit and not ok) else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rungs", default="v22,tie11,tieoff")
    ap.add_argument("--sets", default="S1,S2,S3,S4")
    ap.add_argument("-j", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--out", default=str(SC / "wrong_emission.jsonl.gz"))
    a = ap.parse_args()
    jobs = []
    for rung in a.rungs.split(","):
        for s in a.sets.split(","):
            eps_pts, names = grid(s)
            for nm in names:
                for eps in eps_pts:
                    for t0 in T0:
                        jobs.append((rung, s, nm, eps, t0))
    print("%d decodes" % len(jobs))
    with mp.Pool(a.j) as pool:
        rows = pool.map(one, jobs, chunksize=128)
    with gzip.open(a.out, "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        k = (r[0], r[1])
        agg[k][0] += 1
        agg[k][1] += r[6]
        agg[k][2] += r[7]
        agg[k][3] += r[6] - r[7]
    print("%-8s %-4s %8s %9s %9s %7s %9s" %
          ("rung", "set", "decodes", "emitted", "correct", "WRONG", "wrong%"))
    for k in sorted(agg):
        n, em, ok, wr = agg[k]
        print("%-8s %-4s %8d %9d %9d %7d %8.4f%%" %
              (k[0], k[1], n, em, ok, wr, 100.0 * wr / em if em else 0.0))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
