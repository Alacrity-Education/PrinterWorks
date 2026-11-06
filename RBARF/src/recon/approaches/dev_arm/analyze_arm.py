#!/usr/bin/env python3
"""Attribute every refusal in an arm-investigation run (INVESTIGATION ONLY).

Per captured frame: telemetry (arm-entry phase, arm wait, unarmed gap,
render position), and for every dumped capture the burst geometry, a host
re-decode at the SHIPPED v2.3 production constants (chip-vs-host
divergence), and a (t0, eps) fit against the calibrated sampler model with
t0 searched over 0..4000 ns so a HEAD-CHOPPED (partial) burst shows up as
t0 >= 1250 ns (one WS2812 bit = 1250 ns).

Writes <run>_analysis.jsonl and prints the aggregate tables.
"""
import argparse
import json
import multiprocessing as mp
import statistics as S
import sys
from collections import Counter
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import armlib as A                                              # noqa: E402
from synth import BIT_NS                                        # noqa: E402

T0_MAX = 4000.0
FIRST_BR_NS = 250.0        # decode.c FIRST_BR = 4 cycles: the position the
                           # scanner FABRICATES for the first rise (no
                           # preceding low sample exists at arm entry)
TU_PER_NS = 512.0 / BIT_NS


def fit_wide(bits, raw):
    ref = A.levels(raw)[:A.N_FIT * 8]
    best = None
    for ph in range(0, int(T0_MAX) + 1, 10):
        for j in range(-6, 4):
            eps = -0.0107 + j * 5e-4
            a, _ = A._agree(bits, eps, float(ph), ref)
            if best is None or a > best[0]:
                best = (a, float(ph), eps)
    a0, ph0, eps0 = best
    sp, se = 8.0, 2e-4
    while sp > 0.02:
        moved = False
        for dp, de in ((sp, 0), (-sp, 0), (0, se), (0, -se),
                       (sp, se), (sp, -se), (-sp, se), (-sp, -se)):
            a, _ = A._agree(bits, eps0 + de, ph0 + dp, ref)
            if a > a0:
                a0, ph0, eps0, moved = a, ph0 + dp, eps0 + de, True
        if not moved:
            sp /= 2.0
            se /= 2.0
    return ph0, eps0, a0 / len(ref)


def work(r):
    t = r["tel"]
    o = {k: r[k] for k in ("pattern", "rep", "i", "t_send", "t_report")}
    o.update(
        chip_status=t["status"], chip_cause=t["cause"],
        chip_eps=t["eps_centi"],
        arm_span=A.u16d(t["t_arm1"], t["t_arm0"]),
        arm_wait=A.u16d(t["t_arm1"], t["t_arm0"]) - 720,
        gap_unarmed=A.u16d(t["t_arm0"], t["t_prev_arm1"]),
        render_len=A.u16d(t["t_r1"], t["t_r0"]),
        arm_after_render=A.u16d(t["t_arm0"], t["t_r1"]),
        n_timeout=t["n_timeout"], has_dump=bool(r["cap"]))
    if not r["cap"]:
        return o
    raw = bytes.fromhex(r["cap"])
    truth = bytes.fromhex(r["sent"])
    g = A.geometry(raw)
    st, out, info, epsc = A.decode(raw)
    t0, eps, agree = fit_wide(A.frame_bits(truth), raw)
    o.update(
        n_rise=g["n_rise"], last_hi=g["last_hi"], span_bits=round(g["span_bits"], 2),
        tail_zero_loops=g["tail_zero_loops"], overrun=g["overrun"],
        host_status=int(st), host_cause=int(info.cause), host_eps=int(epsc),
        K=int(info.K), tau=int(info.tau), viol=int(info.violations),
        infeas=int(info.infeasible), laberr=int(info.label_err),
        n_weak=int(info.n_weak), n_tied=int(info.n_tied),
        n_seg=int(info.n_seg), trials=int(info.trials),
        host_delivered=bool(st in (1, 2) and out == truth),
        host_wrong=bool(st in (1, 2) and out != truth),
        parity=bool(st == t["status"] and int(info.cause) == t["cause"]),
        t0_ns=round(t0, 1), eps_fit=round(eps, 6), agree=round(agree, 5),
        chop_bits=int(t0 // BIT_NS),
        anchor_err_tu=round((t0 - FIRST_BR_NS) * TU_PER_NS, 1))
    return o


def pct(xs, p):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--jobs", type=int, default=20)
    a = ap.parse_args()
    meta, rows, nore = A.load_run(a.run)
    with mp.Pool(a.jobs) as pool:
        res = list(pool.imap(work, rows))
    outp = Path(a.run).with_suffix("").as_posix() + "_analysis.jsonl"
    with open(outp, "w") as f:
        for o in res:
            f.write(json.dumps(o) + "\n")

    nsent = meta["frames_sent"]
    print("=" * 78)
    print("RUN %s   phase=%s  %d frames sent, %d captured (%.1f%%), "
          "%d no-report, %d dumps, resets=%d"
          % (Path(a.run).name, meta["phase"], nsent, len(res),
             100.0 * len(res) / nsent, len(nore),
             sum(1 for o in res if o["has_dump"]), meta["resets"]))
    ch = Counter((o["chip_status"], o["chip_cause"]) for o in res)
    print("\nCHIP VERDICTS (all %d captured frames)" % len(res))
    for (st, cz), n in sorted(ch.items(), key=lambda x: -x[1]):
        print("   %-7s %-11s %4d  (%.1f%% of captured, %.1f%% of sent)"
              % (A.STATUS[st], A.CAUSE[cz], n, 100.0 * n / len(res),
                 100.0 * n / nsent))
    d = [o for o in res if o["has_dump"]]
    print("\nDUMP PARITY (chip vs host at the shipped constants): %d/%d match"
          % (sum(1 for o in d if o["parity"]), len(d)))
    bad = [o for o in d if not o["parity"]]
    for o in bad[:10]:
        print("   DIVERGENCE %s r%s chip=%s/%s host=%s/%s"
              % (o["pattern"], o["rep"], A.STATUS[o["chip_status"]],
                 A.CAUSE[o["chip_cause"]], A.STATUS[o["host_status"]],
                 A.CAUSE[o["host_cause"]]))
    hd = [o for o in d if o["host_delivered"]]
    hr = [o for o in d if o["chip_status"] == 0 and o["host_delivered"]]
    print("   host DELIVERS %d/%d dumps; of those the chip REFUSED %d "
          "(host-vs-chip delivery divergence)" % (len(hd), len(d), len(hr)))
    print("   host WRONG emissions on dumps: %d"
          % sum(1 for o in d if o["host_wrong"]))

    print("\nBURST GEOMETRY / PARTIAL-BURST TEST, by chip verdict")
    print("   %-11s %4s | %-22s | %-20s | %s"
          % ("verdict", "n", "t0 (ns) p10/p50/p90 max", "span_bits p10/p50",
             "chop>=1bit  overrun"))
    groups = {}
    for o in d:
        key = A.CAUSE[o["chip_cause"]] if o["chip_status"] == 0 \
              else A.STATUS[o["chip_status"]]
        groups.setdefault(key, []).append(o)
    for k in sorted(groups, key=lambda x: -len(groups[x])):
        gg = groups[k]
        t0s = [o["t0_ns"] for o in gg]
        sbs = [o["span_bits"] for o in gg]
        print("   %-11s %4d | %6.0f %6.0f %6.0f %6.0f | %8.2f %8.2f      | "
              "%2d          %d"
              % (k, len(gg), pct(t0s, .1), pct(t0s, .5), pct(t0s, .9),
                 max(t0s), pct(sbs, .1), pct(sbs, .5),
                 sum(1 for o in gg if o["chop_bits"] >= 1),
                 sum(1 for o in gg if o["overrun"])))
    print("\nDECODER INTERNALS, by chip verdict (medians)")
    print("   %-11s %4s %7s %6s %6s %7s %7s %6s %6s %7s"
          % ("verdict", "n", "K", "tau", "viol", "infeas", "laberr",
             "nweak", "nseg", "agree"))
    for k in sorted(groups, key=lambda x: -len(groups[x])):
        gg = groups[k]
        print("   %-11s %4d %7d %6d %6d %7d %7d %6d %6d %7.4f"
              % (k, len(gg), S.median([o["K"] for o in gg]),
                 S.median([o["tau"] for o in gg]),
                 S.median([o["viol"] for o in gg]),
                 S.median([o["infeas"] for o in gg]),
                 S.median([o["laberr"] for o in gg]),
                 S.median([o["n_weak"] for o in gg]),
                 S.median([o["n_seg"] for o in gg]),
                 S.median([o["agree"] for o in gg])))

    print("\nt0 -> OUTCOME (dumps only; t0 = arm trigger phase, "
          "the scanner fabricates %.0f ns)" % FIRST_BR_NS)
    edges = [0, 300, 400, 500, 600, 700, 800, 900, 1250, 4000]
    print("   %-14s %5s %8s %8s %8s %8s" % ("t0 bin (ns)", "n", "deliv",
                                            "R3", "R1", "other"))
    for lo, hi in zip(edges, edges[1:]):
        gg = [o for o in d if lo <= o["t0_ns"] < hi]
        if not gg:
            continue
        dv = sum(1 for o in gg if o["chip_status"] in (1, 2))
        r3 = sum(1 for o in gg if o["chip_cause"] == 3)
        r1 = sum(1 for o in gg if o["chip_cause"] == 1)
        print("   %5d..%-8d %5d %8d %8d %8d %8d"
              % (lo, hi, len(gg), dv, r3, r1, len(gg) - dv - r3 - r1))

    print("\nARM TELEMETRY (all captured frames), by chip verdict")
    print("   %-11s %4s %-24s %-24s %s"
          % ("verdict", "n", "arm wait us p10/p50/p90", "unarmed gap us "
             "p50/p90/max", "n_timeout p50"))
    g2 = {}
    for o in res:
        key = A.CAUSE[o["chip_cause"]] if o["chip_status"] == 0 \
              else A.STATUS[o["chip_status"]]
        g2.setdefault(key, []).append(o)
    for k in sorted(g2, key=lambda x: -len(g2[x])):
        gg = g2[k]
        w = [o["arm_wait"] for o in gg]
        gp = [o["gap_unarmed"] for o in gg]
        print("   %-11s %4d %6d %6d %6d          %6d %6d %6d      %6d"
              % (k, len(gg), pct(w, .1), pct(w, .5), pct(w, .9),
                 pct(gp, .5), pct(gp, .9), max(gp),
                 S.median([o["n_timeout"] for o in gg])))
    big = [o for o in res if o["gap_unarmed"] > 100]
    print("   frames whose arm window opened <100 us after the previous "
          "one: %d/%d (%.1f%%);  >100 us (a render ran in the gap): %d "
          "(%.1f%%)" % (len(res) - len(big), len(res),
                        100.0 * (len(res) - len(big)) / len(res), len(big),
                        100.0 * len(big) / len(res)))
    if big:
        dv = sum(1 for o in big if o["chip_status"] in (1, 2))
        print("   of those %d 'first arm after a render' captures: "
              "%d delivered, %d refused (%s)"
              % (len(big), dv, len(big) - dv,
                 dict(Counter(A.CAUSE[o["chip_cause"]] for o in big
                              if o["chip_status"] == 0))))
    rl = [o["render_len"] for o in res]
    print("\nRENDER (measured on silicon): len us p10 %d  p50 %d  p90 %d  "
          "max %d" % (pct(rl, .1), pct(rl, .5), pct(rl, .9), max(rl)))
    print("\nBY PATTERN (captured frames): delivered / refused(cause)")
    for pat in sorted({o["pattern"] for o in res}):
        gg = [o for o in res if o["pattern"] == pat]
        dv = sum(1 for o in gg if o["chip_status"] in (1, 2))
        cz = Counter(A.CAUSE[o["chip_cause"]] for o in gg
                     if o["chip_status"] == 0)
        print("   %-13s %2d/%2d  %s" % (pat, dv, len(gg), dict(cz) or ""))
    print("\nwrote %s" % outp)


if __name__ == "__main__":
    main()
