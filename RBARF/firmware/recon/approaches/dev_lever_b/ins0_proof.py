#!/usr/bin/env python3
"""SIZE LEVER (new, not in PROD_CLOSURE SS15.0's list): the SS6 dead-window
tie mark tests `a_hat in ins[:2]`, and that test is ALWAYS TRUE.

Proof.  `inter[a]` means one of hypothesis a's fall positions lies inside
the bracket, and a boundary inside (u, v] has hinge cost 0, so
costs[a] == 0.  argmin's key is (cost, NOT interior, index) ascending
(embedded_v2._decide, decode.c argmin_ab, decode_asm.s argmin -- all
three identical), so whenever ins is non-empty the winner is the FIRST
interior index: cost 0 beats every positive cost, `interior` beats
`not interior` at equal cost, and the lowest index breaks the remaining
tie.  Hence a_hat == ins[0], so `a_hat in ins[:2]` cannot be false and
`ins1` is never read.

Dropping the test and the ins1 tracking is worth 26 B of STM8 assembly.
This script is the empirical half of the proof: it asserts
a_hat == ins[0] on every segment of every capture in every corpus and
both fuzz sets.
"""
import json
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(SC))
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
import dwlib                                                   # noqa: E402
from harness import linearize, load_dataset                    # noqa: E402

EPS = [round(-0.03 + i * 0.0025, 6) for i in range(26)]
ARM = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
_E = {}


def ref(nd, chk=6, check=True):
    key = (nd, chk, check)
    if key not in _E:
        m = dwlib.load_ref()
        m._configure(nd, check=check, chk=chk)
        _E[key] = m
    return _E[key]


def one(job):
    nd, chk, check, samples = job
    e = ref(nd, chk, check)
    seed = e._seed(samples)
    if seed is None:
        return (0, 0)
    K, tau, _ = seed
    for _ in range(2):
        K, tau = e._refine(samples, K, tau)
    cal = e._calibrate(samples, K, tau)
    nseg = bad = 0
    for (k0, k1, u, v, fam) in e._seg_stream(samples, K, tau):
        if k0 >= e.NB:
            continue
        a_hat, _c, _co, lo, hi, inter, _af = e._decide(k0, k1, u, v, fam, cal)
        ins = [a for a in range(lo, hi + 1) if inter[a]]
        nseg += 1
        if ins and a_hat != ins[0]:
            bad += 1
    return (nseg, bad)


def main():
    import v23lib as L
    import fuzz_v23
    jobs = [(48, 6, True, L.linearize(L.capture(d, e, t)))
            for _p, d in L.prod_payloads().items() for e in EPS for t in ARM]
    for fn in ("captures_v23.json", "captures_v23_val.json"):
        for c in json.loads((NEWIMPL / "data" / fn).read_text())["captures"]:
            jobs.append((16, 6, True, linearize(c["capture"])))
    for chk, files in ((3, ("captures_v21.json", "captures_v21_val.json")),
                       (4, ("captures_v22.json", "captures_v22_val.json"))):
        for f in files:
            _m, caps = load_dataset(str(NEWIMPL / "data" / f))
            for c in caps:
                jobs.append((16, chk, True, linearize(c["capture"])))
    _m, caps = load_dataset(str(NEWIMPL / "data" / "captures_trim.json"))
    for c in caps:
        jobs.append((16, 4, False, linearize(c["capture"])))
    for nd in (16, 48):
        ref(nd)
        for (_t, raw, _tr, _cl) in fuzz_v23.cases(nd):
            jobs.append((nd, 6, True, linearize(raw.hex())))
    with mp.Pool(20) as p:
        rows = p.map(one, jobs, chunksize=8)
    nseg = sum(r[0] for r in rows)
    bad = sum(r[1] for r in rows)
    print("captures: %d   segments decided: %d" % (len(jobs), nseg))
    print("segments where ins is non-empty and a_hat != ins[0]: %d" % bad)
    print("VERDICT:", "PROVEN -- ins1 and the a_hat test are dead code"
          if bad == 0 else "COUNTEREXAMPLE FOUND, do not take the lever")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
