#!/usr/bin/env python3
"""Bulk v2.3 parity: decode.c vs embedded_v2.py over a large synthetic
grid at BOTH geometries, so the chase paths (not just the fuzz cases)
are covered.  Diffs the same contract as parity_v23.py."""
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import v23lib as L                                              # noqa: E402
import parity_v23 as P                                          # noqa: E402
from relax_ladder import PAY                                     # noqa: E402

EPS = [round(-0.08 + i * 0.0025, 6) for i in range(65)]
T0 = [375.0, 470.0, 560.0, 650.0, 736.0]
_S = {}


def one(job):
    nd, name, eps, t0 = job
    key = nd
    if key not in _S:
        # LOAD the .so the parent already built -- a worker must never
        # rebuild it: several workers would write the same path at once
        # and one of them would dlopen a half-written file.
        import ctypes
        so = SC / ("parity_host_%d_1_6.so" % nd)
        lib = ctypes.CDLL(str(so))
        lib.ws_decode_ex.restype = ctypes.c_uint8
        lib.ws_decode_ex.argtypes = [ctypes.c_char_p, ctypes.c_uint16,
                                     ctypes.c_char_p]
        ev = P.load_ref()
        ev._configure(nd, chk=6)
        _S[key] = (lib, ev)
    lib, ev = _S[key]
    if nd == 48:
        data = PAY[name]
    else:
        data = L.test_payloads()[name]
    raw = L.capture(data, eps, t0)
    fails = []
    P.compare(lib, ev, nd, raw, "%s %s %.4f %.0f" % (nd, name, eps, t0),
              fails)
    return fails


def main():
    # pre-build BOTH .so files in the parent: the workers must not race
    # to write the same file (they would read a half-written library).
    for nd in (16, 48):
        P.build(nd, True, 6)
    jobs = []
    for name in PAY:
        for eps in EPS:
            for t0 in T0:
                jobs.append((48, name, eps, t0))
    tp = list(L.test_payloads())
    for name in tp:
        for eps in EPS:
            for t0 in T0:
                jobs.append((16, name, eps, t0))
    print("%d parity comparisons" % len(jobs))
    with mp.Pool(23) as p:
        res = p.map(one, jobs, chunksize=64)
    bad = [f for r in res for f in r]
    print("MISMATCHES: %d of %d" % (len(bad), len(jobs)))
    for t, r in bad[:12]:
        print("   ", t, r[:5])
    print("BULK PARITY:", "PASS" if not bad else "FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
