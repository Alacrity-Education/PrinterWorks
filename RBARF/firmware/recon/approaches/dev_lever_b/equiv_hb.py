#!/usr/bin/env python3
"""PROOF that SS6.4's stateless off < DW_OFF_MAX form is bit-identical to
the latched running-hb form it replaces, over every corpus and both fuzz
sets.  The stateless form is what decode.c and decode_asm.s implement."""
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
import importlib.util                                          # noqa: E402
from harness import linearize                                  # noqa: E402

EPS = [round(-0.03 + i * 0.0025, 6) for i in range(26)]
ARM = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
K = ("path", "cause", "trials", "comps", "n_refs", "ref_split",
     "n_weak", "n_tied", "n_dw")
_M = {}


def load_hb():
    spec = importlib.util.spec_from_file_location(
        "ev2_hb", SC / "ev2_running_hb.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mods(nd):
    if nd not in _M:
        a = dwlib.load_ref()
        a._configure(nd)
        b = load_hb()
        b._configure(nd)
        _M[nd] = (a, b)
    return _M[nd]


def one(job):
    nd, pat, s = job
    a, b = mods(nd)
    oa, ia = a.decode_ex(s)
    ob, ib = b.decode_ex(s)
    d = []
    if oa != ob:
        d.append(("bytes", oa.hex() if oa else None,
                  ob.hex() if ob else None))
    for k in K:
        if (ia.get(k) or 0) != (ib.get(k) or 0):
            d.append((k, ia.get(k), ib.get(k)))
    return (pat, d)


def main():
    import v23lib as L
    import fuzz_v23
    jobs = [(48, p, L.linearize(L.capture(d, e, t)))
            for p, d in L.prod_payloads().items() for e in EPS for t in ARM]
    for fn in ("captures_v23.json", "captures_v23_val.json"):
        for c in json.loads((NEWIMPL / "data" / fn).read_text())["captures"]:
            jobs.append((16, c["pattern"], linearize(c["capture"])))
    for nd in (16, 48):
        mods(nd)
        for (tag, raw, _tr, _cl) in fuzz_v23.cases(nd):
            jobs.append((nd, tag, linearize(raw.hex())))
    with mp.Pool(20) as p:
        rows = p.map(one, jobs, chunksize=8)
    bad = [r for r in rows if r[1]]
    print("SS6.4 stateless (off < 64) vs latched running-hb")
    print("frames compared: %d   DIFFERING: %d" % (len(rows), len(bad)))
    for r in bad[:10]:
        print("  ", r)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
