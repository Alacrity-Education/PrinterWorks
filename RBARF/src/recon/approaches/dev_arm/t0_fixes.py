#!/usr/bin/env python3
"""Locate the t0 cliff exactly and size every candidate repair, host-side.

  1. fit accuracy: fit synthetic captures of KNOWN t0 -> the error bar on
     the bench's fitted t0 values;
  2. the safe window: sweep t0 from 0 with the SHIPPED decoder;
  3. mechanism: at the cliff, what changes in the sample-to-bit census;
  4. repairs, each measured over the fatal band:
       R-a  GATE_INFEAS relaxed (one constant, zero flash)
       R-b  ignore the leading UNBRACKETED pulse (the arm enters _cap_loop
            mid-pulse, so the first pulse has no preceding low sample)
       R-c  shift the arm's t0 down by N cycles (firmware; the legacy
            blocking entry's t0 band is 254..501 ns)
     and for each: delivered / WRONG / cause mix.
INVESTIGATION ONLY.
"""
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
from synth import (BIT_NS, SLOT_OFFSET_NS, BRANCH_COST_NS, T1H_NS,  # noqa
                   T0H_NS)
import t0_sweep as T                                            # noqa: E402


def ref():
    sp = importlib.util.spec_from_file_location(
        "ev_f", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    m._configure(48, chk=6)
    return m


def blank_lead(cap):
    """Zero the capture's leading HIGH run: the decoder then anchors on the
    first fully bracketed rise instead of the arm's mid-pulse entry."""
    lv = list(A.levels(cap))
    j = 0
    while j < len(lv) and lv[j]:
        lv[j] = 0
        j += 1
    return T.pack(lv), j


def job(args):
    kind, name, data, t0, val = args
    bits = A.frame_bits(data)
    cap = T.synth_cap(bits, t0)
    if kind == "shipped":
        st, out, info, epsc = A.decode(cap)
        return dict(kind=kind, pattern=name, t0=t0, val=val,
                    delivered=bool(st in (1, 2) and out == data),
                    wrong=bool(st in (1, 2) and out != data),
                    cause=int(info.cause), infeas=int(info.infeasible),
                    viol=int(info.violations), K=int(info.K))
    ev = ref()
    if kind == "gate":
        ev.GATE_INFEAS = val
    if kind == "blank":
        cap, _ = blank_lead(cap)
    out, info = ev.decode_ex(T.ev_linearize(cap))
    return dict(kind=kind, pattern=name, t0=t0, val=val,
                delivered=bool(out == data), wrong=bool(out is not None
                                                        and out != data),
                cause=info["cause"], infeas=info.get("infeasible", 0),
                viol=info.get("violations", 0), K=info.get("K", 0))


def fit_accuracy(FR):
    print("1. FIT ACCURACY (synthetic captures of known t0, fitted with the "
          "same estimator used on the bench dumps)")
    import analyze_arm as AA
    rows = []
    for name, data in FR[:4]:
        bits = A.frame_bits(data)
        for t0 in (300.0, 450.0, 600.0, 700.0, 850.0):
            cap = T.synth_cap(bits, t0)
            f_t0, f_eps, ag = AA.fit_wide(bits, cap)
            rows.append((name, t0, f_t0, f_eps, ag))
            print("   %-13s true t0 %6.1f -> fitted %6.1f  (err %+6.1f ns)  "
                  "eps %+.4f%%  agree %.4f"
                  % (name, t0, f_t0, f_t0 - t0, f_eps * 100, ag))
    errs = [r[2] - r[1] for r in rows]
    print("   fitted-t0 error: mean %+.1f ns, max |err| %.1f ns"
          % (sum(errs) / len(errs), max(abs(e) for e in errs)))
    return rows


def census(FR):
    print("\n3. MECHANISM: sample-to-bit census of the FIRST bit period "
          "versus t0 (slot offsets %s, BIT=%.0f ns, T1H=%.0f ns)"
          % (SLOT_OFFSET_NS, BIT_NS, T1H_NS))
    name, data = FR[0]
    bits = A.frame_bits(data)
    for t0 in (600.0, 660.0, 680.0, 690.0, 700.0, 760.0):
        wsum = 0.0
        cells = []
        for s in range(4):
            a = SLOT_OFFSET_NS[s] + wsum
            t = t0 + a / (1.0 - 0.0107)
            k = int(t // BIT_NS)
            hi = (t - k * BIT_NS) < (T1H_NS if bits[k] else T0H_NS)
            if hi:
                wsum += BRANCH_COST_NS[s]
            cells.append("s%d@%.0f->bit%d%s" % (s, t, k, "H" if hi else "L"))
        print("   t0=%6.1f : %s" % (t0, "  ".join(cells)))


def main():
    FR = T.payloads()
    fit_accuracy(FR)

    print("\n2. SAFE WINDOW, shipped decoder (t0 from 0)")
    t0s = [float(x) for x in range(0, 761, 10)]
    tasks = [("shipped", n, d, t, 0) for (n, d) in FR for t in t0s]
    with mp.Pool(20) as p:
        rows = list(p.imap(job, tasks, chunksize=8))
    edges = list(range(0, 761, 40))
    print("   %-11s %5s %7s %7s %7s" % ("t0 (ns)", "n", "deliv", "R3",
                                        "other"))
    for lo, hi in zip(edges, edges[1:]):
        g = [r for r in rows if lo <= r["t0"] < hi]
        if not g:
            continue
        dv = sum(1 for r in g if r["delivered"])
        r3 = sum(1 for r in g if r["cause"] == 3)
        print("   %4d..%-6d %5d %7d %7d %7d"
              % (lo, hi, len(g), dv, r3, len(g) - dv - r3))
    ok = [r["t0"] for r in rows if r["delivered"]]
    print("   SAFE t0 WINDOW (shipped decoder, all 10 payloads): "
          "%.0f .. %.0f ns" % (min(ok), max(ok)))
    bad3 = sorted({r["t0"] for r in rows if r["cause"] == 3})
    print("   first R3 t0 = %s ns" % (bad3[0] if bad3 else None))

    census(FR)

    print("\n4. REPAIRS over the FATAL BAND t0 = 700..1240 ns "
          "(%d payloads x %d points)" % (len(FR), 28))
    fatal = [float(x) for x in range(700, 1241, 20)]
    res = {}
    tasks = []
    for (n, d) in FR:
        for t in fatal:
            tasks.append(("shipped", n, d, t, 0))
            tasks.append(("blank", n, d, t, 0))
            for gv in (60, 120, 240, 480):
                tasks.append(("gate", n, d, t, gv))
    with mp.Pool(20) as p:
        rr = list(p.imap(job, tasks, chunksize=8))
    (SC / "t0_fixes.jsonl").write_text("\n".join(json.dumps(r) for r in rr))
    for key in [("shipped", 0), ("blank", 0)] + [("gate", g) for g in
                                                 (60, 120, 240, 480)]:
        g = [r for r in rr if (r["kind"], r["val"]) == key]
        if not g:
            continue
        dv = sum(1 for r in g if r["delivered"])
        wr = sum(1 for r in g if r["wrong"])
        cz = Counter(r["cause"] for r in g if not r["delivered"])
        print("   %-8s %-5s  delivered %3d/%3d (%5.1f%%)  WRONG %d   %s"
              % (key[0], key[1] or "", dv, len(g), 100.0 * dv / len(g), wr,
                 dict(cz)))

    print("\n5. REPAIR R-c: shift the arm's t0 down by N cycles (62.5 ns "
          "each).  Applied to the MEASURED bench t0 distribution.")
    an = [json.loads(l) for l in
          open(SC / "arm_run_a_analysis.jsonl")]
    d = [o for o in an if o.get("has_dump") and o.get("t0_ns") is not None]
    # de-bias: refusals are always dumped, successes 1-in-4
    nref = sum(1 for o in an if o["chip_status"] == 0)
    nsuc = sum(1 for o in an if o["chip_status"] != 0)
    dref = sum(1 for o in d if o["chip_status"] == 0)
    dsuc = sum(1 for o in d if o["chip_status"] != 0)
    wsuc = nsuc / dsuc if dsuc else 0
    print("   weights: %d refusals dumped/%d total (w=1.00), "
          "%d successes dumped/%d total (w=%.2f)"
          % (dref, nref, dsuc, nsuc, wsuc))
    unchopped = [o for o in d if o["chop_bits"] == 0]
    CLIFF = min(bad3) if bad3 else 700.0
    for shift_cy in (0, 1, 2, 3, 4):
        sh = shift_cy * 62.5
        over = sum((1.0 if o["chip_status"] == 0 else wsuc)
                   for o in unchopped if o["t0_ns"] - sh >= CLIFF)
        tot = sum((1.0 if o["chip_status"] == 0 else wsuc)
                  for o in unchopped)
        print("   shift %d cy (%5.1f ns): %5.1f of %5.1f complete-burst "
              "captures still above the %.0f ns cliff (%.1f%%)"
              % (shift_cy, sh, over, tot, CLIFF, 100.0 * over / tot))


if __name__ == "__main__":
    main()
