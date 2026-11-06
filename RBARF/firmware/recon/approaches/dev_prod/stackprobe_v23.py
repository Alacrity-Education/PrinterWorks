#!/usr/bin/env python3
"""Empirical v2.3 decode-path stack measurement, PRODUCTION geometry.

The whole decoder is hand assembly now (decode_asm.s carries the
streaming layer AND the pipeline tail), so the CFG analyser
(dev_fw/stackscan2.py, SDCC-shaped labels) cannot walk it.  Instead:
paint the RAM below the live SP with a sentinel, run one decode in ucsim
to the sim_done breakpoint, and read the low-water mark.  Stack depth is
cycle-count independent, so ucsim IS authoritative here (unlike timing).

Cases are drawn from dev_prod/fuzz_v23.py and ranked by the reference's
own comps/trials counts, so the DEEPEST call chain -- chase ->
try_trial -> ref_build -> rank3 -> putval -- is exercised, plus a direct
emit and a refusal for contrast.

Every ucsim child runs under `setsid timeout -k` (ucsim_v23.Ucsim) and a
pkill sweep follows; the harness asserts zero strays at exit.
"""
import re
import subprocess
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import ucsim_v23 as U                                            # noqa: E402
import v23lib as L                                               # noqa: E402
import fuzz_v23                                                  # noqa: E402

SENTINEL = 0xA5
PORT = 21955


def read_chunked(sim, addr, n, chunk=96):
    out = []
    a = addr
    while len(out) < n:
        k = min(chunk, n - len(out))
        v = sim.read(a, k)
        if len(v) != k:
            raise RuntimeError("short read at 0x%X (%d/%d)" % (a, len(v), k))
        out += v
        a += k
    return out


def pick(nd, ev, n=6, by_nweak=False):
    """One direct emit, one refusal, and the n-2 heaviest chases.

    by_nweak also pulls in the cases with the LARGEST n_weak, i.e. the
    ones that fill the A_MAX candidate list and then chase it -- the
    worst case for RAM, which is what a raised A_MAX has to be measured
    against (recon/AMAX_TMAX_SWEEP.md)."""
    rows = []
    for (tag, raw, truth, cls) in fuzz_v23.cases(nd):
        out, info = ev.decode_ex(L.linearize(raw))
        rows.append((tag, raw, info))
    chosen = []
    if by_nweak:
        for r in sorted(rows, key=lambda r: -(r[2].get("n_weak") or 0)):
            if len(chosen) >= max(2, n // 2):
                break
            chosen.append(r)
    for want in ("direct", "chase"):
        for r in rows:
            if r[2]["path"] == want:
                chosen.append(r)
                break
    for r in rows:
        if r[2]["path"] is None:
            chosen.append(r)
            break
    rows.sort(key=lambda r: (-(r[2].get("comps") or 0),
                             -(r[2].get("trials") or 0)))
    for r in rows:
        if len(chosen) >= n:
            break
        if r not in chosen:
            chosen.append(r)
    return chosen[:n]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("nd", nargs="?", type=int, default=48)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--amax", type=int, default=None,
                    help="chase A_MAX (default: the firmware's own 11)")
    ap.add_argument("--tmax", type=int, default=None,
                    help="chase T_MAX (default: the firmware's own 131)")
    ap.add_argument("--by-nweak", action="store_true",
                    help="also include the largest-n_weak cases -- the "
                         "worst case for the A_MAX candidate arrays")
    a = ap.parse_args()
    nd = a.nd
    if (a.amax is None) != (a.tmax is None):
        raise SystemExit("--amax and --tmax must be given together")
    if a.amax is not None:
        U.CHASE[0], U.CHASE[1] = a.amax, a.tmax
        print("chase budget: A_MAX=%d T_MAX=%d (asm .inc + C -D + the "
              "reference)" % (a.amax, a.tmax))
    U.ND = nd
    ev = L.load_ref()
    ev._configure(nd, chk=6)
    if a.amax is not None:
        ev.set_chase_budget(a.amax, a.tmax)
    chosen = pick(nd, ev, a.n, a.by_nweak)
    U.sweep()
    peak_all, rowsout = 0, []
    for k, (tag, raw, info) in enumerate(chosen):
        U.gen_cap(raw)
        sym, mtext = U.link()
        d = re.search(r"^DATA\s+([0-9A-F]{8})\s+([0-9A-F]{8})", mtext, re.M)
        statics_end = int(d.group(1), 16) + int(d.group(2), 16)
        ms = re.search(r"^SSEG\s+([0-9A-F]{8})\s+([0-9A-F]{8})", mtext, re.M)
        if ms:
            statics_end = max(statics_end,
                              int(ms.group(1), 16) + int(ms.group(2), 16))
        dz = re.search(r"^DZP0\s+([0-9A-F]{8})\s+([0-9A-F]{8})", mtext, re.M)
        dzp = int(dz.group(2), 16) if dz else 0
        sim = U.Ucsim(str(SC / "sim_v23.ihx"), PORT + k)
        try:
            st_out = sim.cmd("info registers", 0.3)
            msp = re.search(r"SP=\s*0x([0-9a-fA-F]+)", st_out)
            sp0 = int(msp.group(1), 16) if msp else 0x17FF
            plo = sp0 - 0x18F                       # 400-byte window
            sim.cmd("fill rom 0x%x 0x%x 0x%x" % (plo, sp0, SENTINEL), 0.3)
            got = read_chunked(sim, plo, sp0 - plo + 1)
            if not all(v == SENTINEL for v in got):
                print("paint FAILED (fill unsupported?)")
                return 2
            # SP at the ws_decode_ex entry separates the harness's own
            # frame from the decoder's subtree, which is what the
            # production ledger needs (production main's frame differs).
            sim.cmd("break 0x%x" % sym["_ws_decode_ex"], 0.2)
            sim.cmd_until("run", "Stop at", timeout=60)
            e = sim.cmd("info registers", 0.3)
            me = re.search(r"SP=\s*0x([0-9a-fA-F]+)", e)
            sp_e = int(me.group(1), 16) if me else sp0
            _, at_brk = sim.run_decode(sym["_sim_done"])
            status = sim.read(sym["_g_status"], 1)[0]
            mem = read_chunked(sim, plo, sp0 - plo + 1)
        finally:
            sim.close()
        low = next((plo + i for i, v in enumerate(mem) if v != SENTINEL),
                   None)
        peak = (sp0 + 1 - low) if low is not None else 0
        if low is not None and low <= plo + 8:
            print("WARNING: low-water at the paint floor -- widen it")
        peak_all = max(peak_all, peak)
        sub = sp_e - low if low is not None else 0
        rowsout.append((tag, info, status, peak, statics_end, dzp, at_brk,
                        sub))
        print("  %-42s %-14s nweak=%2d trials=%2d comps=%3d peak=%3d B  "
              "ws_decode_ex subtree=%3d B%s"
              % (tag[:42], info["path"] or info["cause"],
                 info.get("n_weak") or 0,
                 info.get("trials") or 0, info.get("comps") or 0, peak,
                 sub, "" if at_brk else "  RUNAWAY"))
    se, dzp = rowsout[0][4], rowsout[0][5]
    print()
    print("ND=%d  A_MAX=%d T_MAX=%d  DZP0 %d B (0x0001..0x%04X) + "
          "REL DATA/SSEG end 0x%04X"
          % (nd, U.chase_pt()[0], U.chase_pt()[1], dzp, dzp, se))
    print("statics (sim image, incl. the sim harness's own buffers): %d B"
          % (se + 1))
    print("DECODE-PATH STACK PEAK (sim main frame included): %d B" % peak_all)
    print("ws_decode_ex SUBTREE below its entry SP (max): %d B"
          % max(r[7] for r in rowsout))
    r = subprocess.run(["pgrep", "-x", "ucsim_stm8"], capture_output=True)
    print("stray ucsim processes at exit:",
          0 if r.returncode else len(r.stdout.split()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
