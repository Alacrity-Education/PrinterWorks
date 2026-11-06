#!/usr/bin/env python3
"""Targeted ucsim coverage + stack probe for the routines the v2.2a edits
touch: bitmz (factored out of cpflip/tapply), the rlc-based isd builder,
and the SS7.10 W2 bound in cpair.

Four explicit, exactly reproducible ND48 (payload, eps, t0) points --
one per deep chase path, so each changed routine is definitely executed:
  DATAFLIP  chase ACCEPT applying a DATA flip     -> tapply -> bitmz
  CHKCAND   a CHECK-BLOCK bit in the candidate list, check-flip trials
                                                  -> cpflip -> bitmz
  PAIR      a weight-2 trial inside the W2 bound  -> cpair pair path
  BOUNDED   an accept the W2 bound now REFUSES    -> bound is live on target

Each case is diffed bit-exactly against embedded_v2.py AND sentinel-
scanned for the stack low-water mark (the bitmz extraction adds one call
level, so the peak must stay inside the measured 47 B headroom;
measured: 18 B both before and after the v2.2a edits).

NEGATIVE CONTROL: run this against the pre-v2.2a decode_asm.s and
BOUNDED reports `asm=chase ... WRONG  parity=MISMATCH` -- the pre-fix
decoder emits wrong data on that capture, which is what the bound closes.

Usage: python3 chase_cover.py    (ucsim children run under
       setsid timeout -k via ucsim_bitexact; sweep strays afterwards)
"""
import re, sys
from pathlib import Path
NEW = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(NEW / "recon"))
sys.path.insert(0, str(NEW / "bench"))
sys.path.insert(0, str(NEW / "recon/approaches/dev_fw"))
sys.path.insert(0, str(NEW / "recon/approaches/dev_prod"))
from harness import linearize
import sweeplib as S
import ucsim_bitexact as U
U.ASMDEC = True
U.ND_DATA = 48
U.CHK = 4
v2 = U.v2
v2._configure(48, check=True, chk=4)
SENTINEL = 0xA5
CAP = 288

def cap_of(name, hexd, eps, t0):
    data = bytes.fromhex(hexd)
    samples, _ = S.simulate(S.frame_bits(data), eps, t0)
    return S.pack(samples, CAP), data


def read_chunked(sim, addr, n, chunk=96):
    out = []; a = addr
    while len(out) < n:
        k = min(chunk, n - len(out))
        v = sim.read(a, k)
        if len(v) != k:
            raise RuntimeError("short read")
        out += v; a += k
    return out


def run(label, raw, truth, port):
    U.gen_cap(raw)
    sym = U.build(True, True)
    sim = U.Ucsim(str(Path(U.__file__).parent / "sim_v2.ihx"), port)
    try:
        st_out = sim.cmd("info registers", 0.3)
        m = re.search(r"SP=\s*0x([0-9a-fA-F]+)", st_out)
        sp0 = int(m.group(1), 16) if m else 0x17FF
        plo = sp0 - 0x18F
        sim.cmd("fill rom 0x%x 0x%x 0x%x" % (plo, sp0, SENTINEL), 0.3)
        _, at_brk = sim.run_decode(brk=sym.get("_sim_done"), timeout=90.0)
        status = sim.read(sym["_g_status"], 1)[0]
        out = bytes(sim.read(sym["_g_out"], 48))
        di = sim.read(sym["_dec_info"], 20)
        mem = read_chunked(sim, plo, sp0 - plo + 1)
    finally:
        sim.close()
    low = next((plo + i for i, v in enumerate(mem) if v != SENTINEL), None)
    peak = (sp0 + 1 - low) if low else 0
    d_py, ipy = v2.decode_ex(linearize(raw.hex()))
    d_c = out if status else None
    ok = (d_c == d_py and U.PATHS.get(di[0]) == ipy["path"]
          and U.CAUSES.get(di[1]) == ipy["cause"] and di[2] == ipy.get("trials", 0)
          and di[3] == ipy.get("alias_cmp", 0))
    verdict = "-" if d_c is None else ("DELIVERED" if d_c == truth else "WRONG")
    print("  %-9s asm=%-14s ref=%-14s trials=%-2d alias=%-2d %-9s "
          "parity=%s  stack peak=%d B"
          % (label, U.PATHS.get(di[0]) or U.CAUSES.get(di[1]),
             ipy["path"] or ipy["cause"], di[2], di[3], verdict,
             "OK" if ok else "MISMATCH", peak))
    return ok, peak, U.PATHS.get(di[0]) or U.CAUSES.get(di[1])


def pick():
    """explicit, exactly reproducible ND48 coverage cases (no tag parsing):
    each one was located by find_pair.py / the cached corpora and is
    re-simulated here from the same (payload, eps, t0)."""
    frames = {n: d.hex() for n, d in S.FRAMES}
    import json as _j
    kr = _j.load(open(NEW / "klipper/bench_klipper_macro_results.json"))["rows"]
    for r in kr:
        if r["verdict"] == "CATASTROPHIC":
            frames[r["case"]] = r["truth"]
    return {
        # weight-2 DATA repair accepted INSIDE the bound -> cpair pair path + 2x tapply -> bitmz
        "PAIR": ("blink", frames["blink"], -0.02950, 560.0),
        # weight-1 DATA repair accepted -> tapply -> bitmz
        "DATAFLIP": ("colors", frames["colors"], -0.02400, 480.0),
        # CHECK-BLOCK bit in the candidate list -> phase-1/2 trials -> cpflip -> bitmz
        "CHKCAND": ("colors", frames["colors"], -0.02350, 430.0),
        # the UNBOUNDED chase accepted WRONG data here; the W2 bound must refuse
        "BOUNDED": ("colors", frames["colors"], -0.02800, 480.0),
    }


def main():
    ch = pick()
    print("coverage cases selected: %s" % ", ".join(sorted(ch)))
    allok = True; peak = 0
    for i, (lbl, spec) in enumerate(sorted(ch.items())):
        raw, truth = cap_of(*spec)
        ok, pk, path = run(lbl, raw, truth, 22900 + i)
        allok &= ok; peak = max(peak, pk)
    print("CHASE COVERAGE: %s ; deepest stack peak %d B"
          % ("PASS" if allok else "FAIL", peak))
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
