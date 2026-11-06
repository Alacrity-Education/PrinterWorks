#!/usr/bin/env python3
"""A_MAX x T_MAX chase-budget sweep on the NORMATIVE host reference.

  python3 sweep_amax_tmax.py suite      # (a) 70 single-shot payloads x
                                        #     5 eps x 48 arm phases, ND=48
  python3 sweep_amax_tmax.py real       # (b) data/captures_v23.json, ND=16
  python3 sweep_amax_tmax.py wrong -n 20000   # (c) MEASURED false accepts
  python3 sweep_amax_tmax.py validate   # shortcut vs 25 full decodes

Grid: A_MAX in {11,16,22,27,40} x T_MAX in {131,262,393,524,1048}.
Never touches data/captures_val.json.  Never touches the bench.
"""
import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from amaxlib import (GRID, BASE, EPS_GRID, T0_GRID, CAUSE_R, NI,   # noqa
                     make_ref, grid_outcomes, grid_outcomes_full,
                     capture, linearize, CAP_BYTES_PROD)

_EV = {}


def ev_for(nd):
    if nd not in _EV:
        _EV[nd] = make_ref(nd)
    return _EV[nd]


def suite_payloads():
    """The 70 unique payloads of bench/suite_singleshot.py, imported the
    way that script imports its own tables (exec up to main())."""
    p = NI / "bench" / "suite_singleshot.py"
    src = p.read_text()
    i = src.find("\ndef main(")
    ns = {"__name__": "suite_import", "__file__": str(p)}
    sys.path.insert(0, str(NI))
    sys.path.insert(0, str(NI / "bench"))
    exec(compile(src[:i], str(p), "exec"), ns)
    return ns["build_suite"]()


def blank():
    return {"n": 0, "delivered": 0, "wrong": 0, "refused": 0, "domain": 0,
            "cause": Counter(), "path": Counter(),
            "trials": Counter(), "comps": Counter(),
            "chased": 0, "wrong_detail": []}


def fold(acc, res, label=None):
    for p, (v, tag, tr, cp) in res.items():
        d = acc[p]
        if v == "DOMAIN":
            d["domain"] += 1
            continue
        d["n"] += 1
        d["trials"][tr] += 1
        d["comps"][cp] += 1
        if tr:
            d["chased"] += 1
        if v == "DELIVERED":
            d["delivered"] += 1
            d["path"][tag] += 1
        elif v == "WRONG":
            d["wrong"] += 1
            d["path"]["WRONG_" + str(tag)] += 1
            if label is not None and len(d["wrong_detail"]) < 40:
                d["wrong_detail"].append(
                    dict(label=label, path=tag, trials=tr, comps=cp))
        else:
            d["refused"] += 1
            d["cause"][CAUSE_R.get(tag, tag)] += 1


def merge(a, b):
    for p in GRID:
        for k in ("n", "delivered", "wrong", "refused", "chased", "domain"):
            a[p][k] += b[p][k]
        for k in ("cause", "path", "trials", "comps"):
            a[p][k].update(b[p][k])
        a[p]["wrong_detail"] = (a[p]["wrong_detail"]
                                + b[p]["wrong_detail"])[:40]


# ------------------------------------------------------------- corpus (a)
def _suite_task(arg):
    pi, name, data, eps = arg
    ev = ev_for(48)
    acc = {p: blank() for p in GRID}
    chased = 0
    for t0 in T0_GRID:
        lin = linearize(capture(data, eps, t0))
        res, ch = grid_outcomes(ev, lin, data)
        chased += ch
        fold(acc, res, label=f"{name}@eps{eps*100:+.2f}%,t0={t0:.0f}ns")
    return acc, chased


def run_suite(pool):
    suite = suite_payloads()
    tasks = [(i, n, d, e) for i, (f, n, d) in enumerate(suite)
             for e in EPS_GRID]
    acc = {p: blank() for p in GRID}
    nch = 0
    for k, (a, ch) in enumerate(pool.imap_unordered(_suite_task, tasks, 4)):
        merge(acc, a)
        nch += ch
        if (k + 1) % 50 == 0:
            print(f"  ... {k+1}/{len(tasks)} tasks", flush=True)
    print(f"  chase-reaching captures: {nch} of "
          f"{len(suite)*len(EPS_GRID)*len(T0_GRID)}")
    return acc, dict(payloads=len(suite), eps=list(EPS_GRID),
                     n_t0=len(T0_GRID), nd=48, chase_reaching=nch)


# ------------------------------------------------------------- corpus (b)
def _real_task(arg):
    nd, caps = arg
    ev = ev_for(nd)
    acc = {p: blank() for p in GRID}
    ch = 0
    for c in caps:
        truth = bytes.fromhex(c["payload"])[:nd]
        lin = linearize(bytes.fromhex(c["capture"]))
        res, k = grid_outcomes(ev, lin, truth)
        ch += k
        fold(acc, res, label=f"{c['pattern']}#{c['rep']}")
    return acc, ch


def run_real(pool):
    sys.path.insert(0, str(NI / "recon"))
    d = json.loads((NI / "data" / "captures_v23.json").read_text())
    caps = d["captures"]
    n = len(caps)
    chunks = [(16, caps[i::12]) for i in range(12)]
    acc = {p: blank() for p in GRID}
    nch = 0
    for a, ch in pool.imap_unordered(_real_task, chunks):
        merge(acc, a)
        nch += ch
    print(f"  {n} real captures, chase-reaching {nch}")
    return acc, dict(file="data/captures_v23.json", captures=n, nd=16,
                     chase_reaching=nch)


# ------------------------------------------------------------- corpus (c)
STRATA = (
    # (name, weight) -- see _gen_corrupt.  The mix is chosen so the chase
    # is actually REACHED: heavy damage refuses at R3/R2 in the front end
    # and measures nothing about the chase's false-accept exposure.
    ("flip_trim", 6),        # 1-3 random sample-bit flips, trim band
    ("flip_low", 6),         # 1-4 flips in slots R0..R5 only
    ("flip_plateau", 3),     # 1-6 flips over the delivery plateau
    ("wide_eps", 3),         # clean but eps +-8 %: the R7 carriers, i.e.
                             # exactly the frames a bigger A_MAX RE-ADMITS
    ("drift_chop", 2),       # drift + trunc/chop, the malformed-arm shapes
)
_STRAT_CDF = []
_acc = 0
for _n, _w in STRATA:
    _acc += _w
    _STRAT_CDF.append((_acc, _n))
_STRAT_TOT = _acc


def _gen_corrupt(rnd):
    """One corrupted ND=48 frame -> (stratum, payload, raw capture)."""
    r = rnd.randrange(_STRAT_TOT)
    st = next(n for c, n in _STRAT_CDF if r < c)
    data = bytes(rnd.randrange(256) for _ in range(48))
    if st == "flip_trim":
        raw = bytearray(capture(data, rnd.uniform(-0.016, -0.004),
                                rnd.uniform(70.0, 658.0)))
        for _ in range(rnd.choice((1, 2, 3))):
            raw[rnd.randrange(len(raw))] ^= 1 << rnd.randrange(8)
    elif st == "flip_low":
        raw = bytearray(capture(data, rnd.uniform(-0.016, -0.004),
                                rnd.uniform(70.0, 658.0)))
        for _ in range(rnd.choice((1, 2, 3, 4))):
            raw[rnd.randrange(len(raw))] ^= 1 << rnd.randrange(6)
    elif st == "flip_plateau":
        raw = bytearray(capture(data, rnd.uniform(-0.025, 0.0025),
                                rnd.uniform(70.0, 700.0)))
        for _ in range(rnd.choice((1, 2, 4, 6))):
            raw[rnd.randrange(len(raw))] ^= 1 << rnd.randrange(8)
    elif st == "wide_eps":
        raw = bytearray(capture(data, rnd.uniform(-0.08, 0.08),
                                rnd.uniform(70.0, 900.0)))
    else:
        raw = bytearray(capture(data, rnd.uniform(-0.020, 0.002),
                                rnd.uniform(70.0, 900.0),
                                drift=rnd.uniform(-0.012, 0.012),
                                trunc=rnd.choice((0, 2, 4, 8, 16)),
                                chop=rnd.choice((0, 0, 1, 2))))
        for _ in range(rnd.choice((0, 0, 1, 2))):
            if raw:
                raw[rnd.randrange(len(raw))] ^= 1 << rnd.randrange(8)
    return st, data, bytes(raw)


def _wrong_task(arg):
    seed, count = arg
    ev = ev_for(48)
    rnd = random.Random(seed)
    acc = {p: blank() for p in GRID}
    per = {n: {p: blank() for p in GRID} for n, _w in STRATA}
    ch = 0
    for _ in range(count):
        st, data, raw = _gen_corrupt(rnd)
        lin = linearize(raw)
        res, k = grid_outcomes(ev, lin, data)
        ch += k
        fold(acc, res, label=st + ":" + data[:6].hex())
        fold(per[st], res, label=st + ":" + data[:6].hex())
    return acc, ch, per


def run_wrong(pool, n, seed):
    per_task = 40
    tasks = [(seed + i, per_task)
             for i in range((n + per_task - 1) // per_task)]
    acc = {p: blank() for p in GRID}
    strat = {nm: {p: blank() for p in GRID} for nm, _w in STRATA}
    nch = 0
    for k, (a, c, pr) in enumerate(pool.imap_unordered(_wrong_task,
                                                       tasks, 2)):
        merge(acc, a)
        for nm in strat:
            merge(strat[nm], pr[nm])
        nch += c
        if (k + 1) % 100 == 0:
            print(f"  ... {(k+1)*per_task}/{n} frames", flush=True)
    print(f"  chase-reaching {nch} of {len(tasks)*per_task}")
    meta = dict(frames=len(tasks) * per_task, seed=seed, nd=48,
                chase_reaching=nch, strata={n_: w for n_, w in STRATA})
    return acc, meta, strat


# ----------------------------------------------------------- --validate
def _val_task(arg):
    kind, payload, eps, t0 = arg
    ev = ev_for(48)
    lin = linearize(capture(payload, eps, t0))
    fast, _ = grid_outcomes(ev, lin, payload)
    slow = grid_outcomes_full(ev, lin, payload)
    bad = [p for p in GRID if fast[p] != slow[p]]
    return len(bad), bad[:3], (kind, eps, t0)


def run_validate(pool, n, seed):
    suite = suite_payloads()
    rnd = random.Random(seed)
    tasks = []
    for _ in range(n):
        _f, _nm, d = rnd.choice(suite)
        tasks.append(("suite", d, rnd.choice(EPS_GRID), rnd.choice(T0_GRID)))
    for _ in range(n // 2):
        d = bytes(rnd.randrange(256) for _ in range(48))
        tasks.append(("wide", d, rnd.uniform(-0.03, 0.03),
                      rnd.uniform(0.0, 1250.0)))
    bad = tot = 0
    for nb, ex, ctx in pool.imap_unordered(_val_task, tasks, 8):
        tot += 1
        if nb:
            bad += 1
            print("  MISMATCH", ctx, ex)
    print(f"  shortcut validation: {tot - bad}/{tot} captures identical "
          f"across all 25 grid points")
    return bad == 0


def dump(name, acc, meta):
    out = {"meta": meta, "grid": []}
    for p in GRID:
        d = acc[p]
        out["grid"].append({
            "A_MAX": p[0], "T_MAX": p[1], "n": d["n"],
            "delivered": d["delivered"], "wrong": d["wrong"],
            "refused": d["refused"], "chased": d["chased"],
            "domain_excluded": d["domain"],
            "cause": dict(d["cause"]), "path": dict(d["path"]),
            "trials_hist": {str(k): v for k, v in sorted(d["trials"].items())},
            "comps_hist": {str(k): v for k, v in sorted(d["comps"].items())},
            "wrong_detail": d["wrong_detail"]})
    f = HERE / f"sweep_{name}.json"
    f.write_text(json.dumps(out, indent=1))
    print(f"  saved {f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["suite", "real", "wrong", "validate"])
    ap.add_argument("-n", type=int, default=20000)
    ap.add_argument("-j", type=int, default=max(1, (os.cpu_count() or 4) - 4))
    ap.add_argument("--seed", type=int, default=20260908)
    a = ap.parse_args()
    t0 = time.time()
    print(f"[{a.what}] {len(GRID)} grid points, {a.j} workers", flush=True)
    with Pool(a.j) as pool:
        if a.what == "suite":
            acc, meta = run_suite(pool)
        elif a.what == "real":
            acc, meta = run_real(pool)
        elif a.what == "wrong":
            acc, meta, strat = run_wrong(pool, a.n, a.seed)
            for nm, sa in strat.items():
                dump("wrong_" + nm, sa, dict(stratum=nm))
        else:
            ok = run_validate(pool, min(a.n, 4000), a.seed)
            print("VALIDATE:", "PASS" if ok else "FAIL")
            return 0 if ok else 1
    meta["elapsed_s"] = round(time.time() - t0, 1)
    dump(a.what, acc, meta)
    print(f"[{a.what}] {meta['elapsed_s']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
