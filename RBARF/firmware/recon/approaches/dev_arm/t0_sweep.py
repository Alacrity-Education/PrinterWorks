#!/usr/bin/env python3
"""CAUSAL t0 sweep: does the arm trigger phase alone decide R3?

Synthesises captures with recon/synth.py's calibrated sampler at a fixed
eps and a swept t0 (arm trigger phase, edge -> first sample), decodes each
with the SHIPPED v2.3 production decoder (decode.c ND48/CHK6), and reports
delivery / refusal cause versus t0 for all 10 production payloads.

This is the host-side counterpart of the bench t0 -> outcome table: the
bench measures the JOINT distribution (arm t0 x outcome), this isolates
t0 as the only variable.  It also sizes the candidate fixes by re-running
each payload with the two decoder-side anchor repairs applied to the
Python REFERENCE decoder (bit-exact with decode.c):
  A  FIRST_BR: the fabricated first-rise offset, 4 cy -> swept
  B  drop-first-pulse: ignore the first (unbracketed) pulse in the seed
     and the segment stream, anchoring on the first FULLY BRACKETED rise
INVESTIGATION ONLY: writes only into dev_arm/.
"""
import argparse
import importlib.util
import json
import multiprocessing as mp
import sys
from collections import Counter
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(SC))
sys.path.insert(0, str(NEWIMPL / "recon"))
import armlib as A                                              # noqa: E402
from synth import BIT_NS                                        # noqa: E402

CAP = 288
EPS = -0.0107


def payloads():
    import importlib.util as iu
    sp = iu.spec_from_file_location("dp", NEWIMPL / "bench" / "drive_prod.py")
    m = iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m.FRAMES


def pack(lv, nbytes=CAP):
    """cap_code.s capture layout from a flat sample list."""
    out = bytearray(nbytes)
    for i in range(nbytes):
        b = 0
        if i > 0:
            j = (i - 1) * 8
            b |= (lv[j + 6] if j + 6 < len(lv) else 0) << 7
            b |= (lv[j + 7] if j + 7 < len(lv) else 0) << 6
        j = i * 8
        for s in range(6):
            if j + s < len(lv):
                b |= lv[j + s] << (5 - s)
        out[i] = b
    return bytes(out)


def synth_cap(bits, t0, eps=EPS):
    return pack(A.simulate(bits, eps, t0, n_iter=CAP + 1))


def job(args):
    name, data, t0 = args
    bits = A.frame_bits(data)
    cap = synth_cap(bits, t0)
    st, out, info, epsc = A.decode(cap)
    return {"pattern": name, "t0": t0, "status": int(st),
            "cause": int(info.cause), "K": int(info.K), "tau": int(info.tau),
            "infeas": int(info.infeasible), "laberr": int(info.label_err),
            "viol": int(info.violations), "n_seg": int(info.n_seg),
            "delivered": bool(st in (1, 2) and out == data),
            "eps_centi": int(epsc)}


def ref_fresh():
    sp = importlib.util.spec_from_file_location(
        "ev_t", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def job_ref(args):
    """Reference decoder with a candidate anchor repair applied."""
    name, data, t0, mode, val = args
    ev = ref_fresh()
    ev._configure(48, chk=6)
    if mode == "first_br":
        ev.FIRST_BR_CY = val
    bits = A.frame_bits(data)
    cap = synth_cap(bits, t0)
    sm = ev_linearize(cap)
    out, info = ev.decode_ex(sm)
    return {"pattern": name, "t0": t0, "mode": mode, "val": val,
            "delivered": bool(out == data[:48]),
            "cause": info["cause"]}


def ev_linearize(raw):
    out = []
    n = len(raw)
    for i in range(n):
        b = raw[i]
        for k in range(6):
            out.append((i, k, (b >> (5 - k)) & 1))
        if i + 1 < n:
            nb = raw[i + 1]
            out.append((i, 6, (nb >> 7) & 1))
            out.append((i, 7, (nb >> 6) & 1))
    out.sort(key=lambda s: (s[0], s[1]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lo", type=float, default=200.0)
    ap.add_argument("--hi", type=float, default=1300.0)
    ap.add_argument("--step", type=float, default=10.0)
    ap.add_argument("--jobs", type=int, default=20)
    ap.add_argument("--fixes", action="store_true")
    a = ap.parse_args()
    FR = payloads()
    t0s = [a.lo + i * a.step
           for i in range(int((a.hi - a.lo) / a.step) + 1)]
    tasks = [(n, d, t) for (n, d) in FR for t in t0s]
    with mp.Pool(a.jobs) as p:
        rows = list(p.imap(job, tasks, chunksize=8))
    (SC / "t0_sweep.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows))
    print("=" * 78)
    print("SHIPPED DECODER (decode.c ND48/CHK6), eps = %+.2f%%, "
          "%d payloads x %d t0 points" % (EPS * 100, len(FR), len(t0s)))
    print("   %-9s %5s %8s %8s %8s %8s %s"
          % ("t0 (ns)", "n", "deliv", "R3", "R1", "other", "median infeas"))
    import statistics as S
    edges = list(range(int(a.lo), int(a.hi) + 1, 50))
    for lo, hi in zip(edges, edges[1:]):
        g = [r for r in rows if lo <= r["t0"] < hi]
        if not g:
            continue
        dv = sum(1 for r in g if r["delivered"])
        r3 = sum(1 for r in g if r["cause"] == 3)
        r1 = sum(1 for r in g if r["cause"] == 1)
        print("   %4d..%-4d %5d %8d %8d %8d %8d %8d"
              % (lo, hi, len(g), dv, r3, r1, len(g) - dv - r3 - r1,
                 S.median([r["infeas"] for r in g])))
    # the exact threshold, per payload
    print("\nPER-PAYLOAD R3 THRESHOLD (highest t0 that still delivers, and "
          "the first t0 that refuses R3)")
    for n, _ in FR:
        g = sorted((r for r in rows if r["pattern"] == n),
                   key=lambda r: r["t0"])
        last_ok = max((r["t0"] for r in g if r["delivered"]), default=None)
        first_r3 = min((r["t0"] for r in g if r["cause"] == 3), default=None)
        print("   %-13s last delivered t0 = %s ns   first R3 t0 = %s ns"
              % (n, last_ok, first_r3))
    allr3 = [r["t0"] for r in rows if r["cause"] == 3]
    alldv = [r["t0"] for r in rows if r["delivered"]]
    if allr3:
        print("\n   R3 t0 range %.0f..%.0f ns; delivered t0 range %.0f..%.0f"
              % (min(allr3), max(allr3), min(alldv), max(alldv)))
        print("   pooled: first R3 at t0 = %.0f ns "
              "(predicted 250 + 160/0.4096 = 640 ns)" % min(allr3))

    if a.fixes:
        print("\n" + "=" * 78)
        print("CANDIDATE ANCHOR REPAIRS, reference decoder (bit-exact with "
              "decode.c), same sweep")
        ftasks = []
        for (n, d) in FR:
            for t in t0s:
                for br in (4, 6, 8, 10, 12, 14, 16, 20):
                    ftasks.append((n, d, t, "first_br", br))
        with mp.Pool(a.jobs) as p:
            fr = list(p.imap(job_ref, ftasks, chunksize=8))
        (SC / "t0_fixes.jsonl").write_text(
            "\n".join(json.dumps(r) for r in fr))
        print("   FIRST_BR (cy)  delivered/total   t0 window that delivers")
        for br in (4, 6, 8, 10, 12, 14, 16, 20):
            g = [r for r in fr if r["val"] == br]
            dv = [r["t0"] for r in g if r["delivered"]]
            print("   %13d  %5d/%-5d      %s"
                  % (br, len(dv), len(g),
                     ("%.0f..%.0f ns" % (min(dv), max(dv))) if dv else "-"))
            print("        causes: %s"
                  % dict(Counter(r["cause"] for r in g if not r["delivered"])))


if __name__ == "__main__":
    main()
