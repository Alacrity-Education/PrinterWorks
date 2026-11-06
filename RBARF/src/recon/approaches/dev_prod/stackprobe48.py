#!/usr/bin/env python3
"""Empirical decode-path stack measurement at PRODUCTION geometry.

The decoder is hand assembly (decode_asm.s), so the CFG stack analyser
(stackscan2.py, SDCC-shaped labels/calls) cannot walk it.  Instead:
paint the RAM above the statics with a sentinel, run one ND48 decode in
ucsim to the HALT, and read the low-water mark.  Stack depth is
cycle-count independent, so ucsim IS authoritative here (unlike timing).

Cases cover the deep paths: direct-CRC emit, chase emit (deepest call
chain), and a corner refusal.  Every ucsim invocation is closed in a
finally:; the caller wraps the whole run in a hard timeout.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                    # recon/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "bench"))
sys.path.insert(0, str(ROOT / "approaches" / "dev_fw"))

from synth import synth_capture           # noqa: E402
from crc import build_payload             # noqa: E402
import ucsim_bitexact as U                # noqa: E402
from smoke48 import pack, payloads        # noqa: E402

U.ASMDEC = True
U.ND_DATA = 48
U.v2._configure(48, check=True)

CAP_BYTES = 288
SENTINEL = 0xA5

def read_chunked(sim, addr, n, chunk=96):
    """sim.read with one dump round-trip per chunk (a 400-byte dump can
    outrun the harness's single 0.25 s drain window)."""
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


CASES = [  # (payload idx, eps, phase_ns, label)
    (0,  0.0,     300.0, "direct"),
    (4,  0.01,    420.0, "mid"),
    (5, -0.02248, 330.0, "trim1"),
    (4,  0.075,   380.0, "corner-refuse"),
    (0, -0.025,   275.0, "band-edge"),
]


def main():
    pls = payloads()
    peak_all = 0
    for n, (pi, eps, ph, label) in enumerate(CASES):
        payload = build_payload(pls[pi])
        raw = pack(synth_capture(payload, eps=eps, phase_ns=ph), CAP_BYTES)
        U.gen_cap(raw)
        sym = U.build(True, True)
        # statics end from the sim map (DATA area addr+size, SSEG +1)
        m = (Path(U.__file__).parent / "sim_v2.map").read_text()
        d = re.search(r"^DATA\s+([0-9A-F]{8})\s+([0-9A-F]{8})", m, re.M)
        lo = int(d.group(1), 16) + int(d.group(2), 16) + 1  # + SSEG marker
        sim = U.Ucsim(str(Path(U.__file__).parent / "sim_v2.ihx"), 21950 + n)
        try:
            # ucsim runs the S208 model: hardware-reset SP = 0x17FF, NOT
            # the S001's 0x3FF.  Read the live SP, paint a window below
            # it (well above the image's DATA end), then low-water scan.
            st_out = sim.cmd("info registers", 0.3)
            msp = re.search(r"SP=\s*0x([0-9a-fA-F]+)", st_out)
            sp0 = int(msp.group(1), 16) if msp else 0x17FF
            plo = sp0 - 0x18F                  # 400-byte window
            sim.cmd("fill rom 0x%x 0x%x 0x%x" % (plo, sp0, SENTINEL), 0.3)
            got = read_chunked(sim, plo, sp0 - plo + 1)
            if not all(v == SENTINEL for v in got):
                print("paint FAILED (fill unsupported?)"); return 2
            _, at_brk = sim.run_decode(brk=sym.get("_sim_done"))
            if not at_brk:
                print("%s RUNAWAY: never reached sim_done" % label)
            st = sim.read(sym["_g_status"], 1)[0]
            mem = read_chunked(sim, plo, sp0 - plo + 1)
        finally:
            sim.close()
        low = None
        for i, v in enumerate(mem):
            if v != SENTINEL:
                low = plo + i
                break
        peak = (sp0 + 1 - low) if low is not None else 0
        if low is not None and low <= plo + 8:
            print("WARNING: low-water at paint floor -- widen the window")
        peak_all = max(peak_all, peak)
        print("%-14s status=%d SP0=0x%04X statics_end=0x%03X low=0x%04X  "
              "peak=%3d B" % (label, st, sp0, lo, low if low else sp0, peak))
    print("DECODE-PATH PEAK (sim main frame incl.): %d B" % peak_all)
    print("(+ prod main frame/call delta and +9 B TIM4 ISR context are"
          " added in the ledger)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
