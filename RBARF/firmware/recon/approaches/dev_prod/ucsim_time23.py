#!/usr/bin/env python3
"""Isolate the v2.3 CHASE's decode-time cost on target.

Same capture, same image, only T_MAX changed (131 vs 1): the tick
difference divided by the comparison difference is the marginal cost of a
residual comparison, which is what the "67 trials ~ 8 ms against a
~180 ms window" claim needs checking against.  ucsim children run under
setsid timeout -k with a pkill sweep, like every other simulator run.
"""
import subprocess
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import ucsim_v23 as U                                            # noqa: E402
import v23lib as L                                               # noqa: E402
import fuzz_v23                                                  # noqa: E402

PICK = ["eps+0.005/kl_preset_draw_rev", "zr[kl_preset_rain] eps+0.0060",
        "chk[all 6 check bytes damaged] eps+0.002/full"]


def run(raw, tmax):
    U._objs = None
    orig = U.cflags
    U.cflags = lambda: orig() + (["-DT_MAX_OVR=%d" % tmax] if tmax else [])
    U.gen_cap(raw)
    sym, _ = U.link()
    sim = U.Ucsim(str(SC / "sim_v23.ihx"), U.PORT)
    try:
        tk, ok = sim.run_decode(sym["_sim_done"])
        di = sim.read(sym["_dec_info"], 23)
    finally:
        sim.close()
    U.cflags = orig
    U._objs = None
    return tk, di[2], di[20], ok


def main():
    ev = L.load_ref()
    ev._configure(48, chk=6)
    cases = {t: raw for (t, raw, _tr, _c) in fuzz_v23.cases(48)}
    U.sweep()
    print("%-46s %7s %6s %6s %10s" % ("case", "T_MAX", "trials", "comps",
                                      "ticks"))
    rows = []
    for tag in PICK:
        raw = cases[tag]
        a = run(raw, 131)
        b = run(raw, 1)
        print("%-46s %7d %6d %6d %10d" % (tag[:46], 131, a[1], a[2], a[0]))
        print("%-46s %7d %6d %6d %10d" % ("", 1, b[1], b[2], b[0]))
        dc = a[2] - b[2]
        dt = a[0] - b[0]
        if dc > 0:
            print("    -> %+d ticks for %+d comparisons = %.0f ticks each "
                  "(%.1f us @16 MHz); full 131-comparison budget = "
                  "%.0f ticks = %.2f ms"
                  % (dt, dc, dt / dc, dt / dc / 16.0, 131 * dt / dc,
                     131 * dt / dc / 16000.0))
            rows.append(dt / dc)
    if rows:
        m = sum(rows) / len(rows)
        print("\nmean %.0f ticks per residual comparison; the WHOLE T_MAX = "
              "131 budget costs %.0f ticks = %.2f ms @16 MHz"
              % (m, 131 * m, 131 * m / 16000.0))
    r = subprocess.run(["pgrep", "-x", "ucsim_stm8"], capture_output=True)
    print("stray ucsim processes at exit:",
          0 if r.returncode else len(r.stdout.split()))


if __name__ == "__main__":
    main()
