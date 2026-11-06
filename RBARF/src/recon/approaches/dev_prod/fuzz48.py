#!/usr/bin/env python3
"""Widened production-geometry ucsim corpus (ND_DATA=48, 288-byte
captures), biased to the REFUSAL and CHASE paths the fixed smoke48 corpus
under-covers -- the input class implicated in the on-silicon ILLOPF reset
(recon/PROD_CLOSURE.md SS7).

Case groups:
  A  eps corners (+/-3..7.5%) with clean payloads       -> emitgate/lock/..
  B  corrupted check blocks (1..3 byte flips, splits)   -> chase check phases
  C  corrupted DATA wire bytes (1..2 flips)             -> chase data phases,
                                                           alias guard, R6-R8
  D  mid-frame trigger (capture starts at bit j > 0)    -> partial frames,
                                                           R1/R2 territory
  E  random bit noise in the PACKED capture bytes       -> scanner stress
  F  eps corner x data corruption                       -> mixed
  G  the 10 bench FRAMES at this unit's real operating
     points (factory -1.09%, converged +0.08%)          -> the silicon mix

Every case runs in ucsim under the PRODUCTION-IDENTICAL link
(ucsim_bitexact.build with ASMDEC: --code-loc 0x8068, --data-loc 0x100,
vectors_sim.s, VGAP link guard) and is diffed bit-exactly against the
Python reference (bytes + path + cause + all counters).  A case that
never reaches _sim_done is a RUNAWAY = the crash reproduced; its capture
is saved for PC localization.

Simulator hygiene: every ucsim_stm8 child is spawned under
`setsid timeout -k 5 120`, and a pkill -x sweep + pgrep check runs after
every case.

Usage: python3 fuzz48.py [--only GROUPS] [--save-dir DIR]
"""
import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                    # recon/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "bench"))
sys.path.insert(0, str(ROOT / "approaches" / "dev_fw"))

import synth                               # noqa: E402
from synth import synth_capture, _simulate # noqa: E402
from crc import build_payload              # noqa: E402
from patterns import frame as wire_frame   # noqa: E402
from harness import linearize              # noqa: E402
import ucsim_bitexact as U                 # noqa: E402

U.ASMDEC = True
U.ND_DATA = 48
v2 = U.v2
v2._configure(48, check=True)

CAP_BYTES = 288

# ---- setsid timeout -k wrapper for EVERY ucsim_stm8 child --------------
_orig_popen = subprocess.Popen


class _WrapPopen:
    def __call__(self, cmd, **kw):
        if cmd and cmd[0] == "ucsim_stm8":
            cmd = ["setsid", "timeout", "-k", "5", "120"] + cmd
        return _orig_popen(cmd, **kw)


subprocess.Popen = _WrapPopen()


def sweep():
    subprocess.run(["pkill", "-x", "ucsim_stm8"], capture_output=True)
    time.sleep(0.15)
    r = subprocess.run(["pgrep", "-x", "ucsim_stm8"], capture_output=True)
    if r.returncode == 0:
        subprocess.run(["pkill", "-9", "-x", "ucsim_stm8"],
                       capture_output=True)
        time.sleep(0.15)


# ---- capture builders ---------------------------------------------------

def pack(samples, nbytes=CAP_BYTES):
    lv = {(i, s): v for (i, s, v) in samples}
    out = bytearray(nbytes)
    for i in range(nbytes):
        b = 0
        if i > 0:
            b |= lv.get((i - 1, 6), 0) << 7
            b |= lv.get((i - 1, 7), 0) << 6
        for s in range(6):
            b |= lv.get((i, s), 0) << (5 - s)
        out[i] = b
    return bytes(out)


def cap_from_payload(payload51, eps, phase):
    return pack(synth_capture(payload51, eps=eps, phase_ns=phase))


def cap_from_wire(wire59, eps, phase, bit_off=0):
    bits = [int(b) for byte in wire59 for b in f"{byte:08b}"]
    return pack(_simulate(bits[bit_off:], eps, 0.0, phase, synth.N_ITER))


def _lcg(seed, n):
    x, out = seed, bytearray()
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


# the 10 bench frames (bench/drive_prod.py FRAMES, verbatim data bytes)
sys.path.insert(0, str(ROOT.parent / "bench"))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "drive_prod", ROOT.parent / "bench" / "drive_prod.py")
# drive_prod imports testprobe at module level; build FRAMES here instead.
COLORS = bytes([0x40, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x40,
                0x40, 0x40, 0x00, 0x00, 0x40, 0x40, 0x40, 0x00, 0x40,
                0x20, 0x20, 0x20, 0x10, 0x08, 0x04])


def _mk(base, flags):
    b = bytearray(24); b[:len(base)] = base
    f = bytearray(24); f[:len(flags)] = flags
    return bytes(b + f)


BENCH_FRAMES = [
    ("colors", _mk(COLORS, [0, 0, 0, 0, 0, 0, 0, 0, 0] + [0] * 14 + [0x02])),
    ("dark", bytes(48)),
    ("full", _mk(bytes([0xFF] * 24), [0, 0, 0, 0, 0, 0, 0, 0, 0] + [0] * 14 + [0x02])),
    ("blink", _mk(COLORS, [0x01, 0x14, 0xA5, 0, 0, 0x30, 0x30, 0x30, 0] + [0] * 14 + [0x02])),
    ("fade", _mk(COLORS, [0x02, 0x28, 0, 0, 0, 0] + [0] * 17 + [0x02])),
    ("seq_plain", _mk(COLORS, [0x03, 0x1E, 0, 0x02, 0, 0x02, 0x00, 0x01, 0x23, 0x45, 0x67, 0xFF] + [0] * 11 + [0x02])),
    ("seq_pause", _mk(COLORS, [0x03, 0x28, 0, 0, 0x04, 0, 0x0C, 0x08, 0x81, 0x18, 0x3F, 0xFF] + [0] * 11 + [0x02])),
    ("preset_spin", _mk(COLORS, [0x03, 0x1E, 0, 0, 0, 0x08, 0x01, 0x01, 0x57, 0x62, 0xFF] + [0] * 12 + [0x02])),
    ("preset_rainR", _mk(COLORS, [0x03, 0x32, 0, 0, 0, 0, 0x02, 0x26, 0x75, 0x10, 0x43, 0xFF] + [0] * 11 + [0x02])),
    ("rnd", _lcg(0xC0FFEE, 48)),
]


def gen_cases():
    """Yield (tag, raw_capture_bytes)."""
    rnd = random.Random(0xD0DEC)
    phases = [254.0, 330.0, 385.0, 440.0, 501.0]

    # A: eps corners, clean payloads
    eps_pts = [-0.075, -0.06, -0.05, -0.04, -0.03, 0.03, 0.04, 0.05, 0.06,
               0.075, -0.029, 0.029]
    for i, eps in enumerate(eps_pts):
        name, data = BENCH_FRAMES[i % 10]
        pay = build_payload(data)
        yield ("A%02d_%s_eps%+.3f" % (i, name, eps),
               cap_from_payload(pay, eps, phases[i % 5]))

    # B: corrupted check blocks
    b_cases = [
        (0, [(48, 0x01)]),                       # 1 flip in check[0]
        (1, [(49, 0x80)]),                       # 1 flip in check[1]
        (2, [(50, 0x10)]),                       # 1 flip in check[2]
        (3, [(48, 0x01), (49, 0x02)]),           # split vote (all differ)
        (4, [(48, 0xFF)]),                       # whole byte inverted
        (5, [(48, 0x03), (49, 0x03)]),           # two equal-wrong: majority wrong
        (6, [(48, 0x01), (49, 0x02), (50, 0x04)]),  # all three differ hard
        (7, [(49, 0x41)]),
        (8, [(50, 0x81), (48, 0x20)]),
        (9, [(48, 0x08)]),
    ]
    eps_b = [0.0, -0.01072, 0.01274, -0.025, 0.0, -0.01072, 0.01274, 0.0,
             -0.025, 0.02]
    for i, (pi, flips) in enumerate(b_cases):
        name, data = BENCH_FRAMES[pi % 10]
        pay = bytearray(build_payload(data))
        for off, mask in flips:
            pay[off] ^= mask
        yield ("B%02d_%s_chk" % (i, name),
               cap_from_payload(bytes(pay), eps_b[i], phases[i % 5]))

    # C: corrupted DATA wire bytes (CRC now mismatches -> chase/refuse)
    for i in range(10):
        name, data = BENCH_FRAMES[i]
        pay = bytearray(build_payload(data))
        pay[rnd.randrange(48)] ^= (1 << rnd.randrange(8))
        if i % 2:
            pay[rnd.randrange(48)] ^= (1 << rnd.randrange(8))
        yield ("C%02d_%s_data" % (i, name),
               cap_from_payload(bytes(pay), [-0.01072, 0.0, 0.008][i % 3],
                                phases[i % 5]))

    # D: mid-frame trigger (capture starts at wire bit j)
    for i, boff in enumerate([40, 100, 200, 300, 400, 460, 24, 470, 150, 350]):
        name, data = BENCH_FRAMES[i % 10]
        wire = wire_frame(build_payload(data))
        yield ("D%02d_%s_bit%d" % (i, name, boff),
               cap_from_wire(wire, [-0.01072, 0.0][i % 2],
                             phases[i % 5], bit_off=boff))

    # E: random bit noise in the packed capture
    for i, nflip in enumerate([1, 2, 4, 8, 16, 3, 6, 12]):
        name, data = BENCH_FRAMES[i % 10]
        raw = bytearray(cap_from_payload(build_payload(data),
                                         [-0.01072, 0.0][i % 2],
                                         phases[i % 5]))
        for _ in range(nflip):
            raw[rnd.randrange(CAP_BYTES)] ^= (1 << rnd.randrange(8))
        yield ("E%02d_%s_n%d" % (i, name, nflip), bytes(raw))

    # F: eps corner x data corruption
    for i, eps in enumerate([-0.05, 0.05, -0.035, 0.035, -0.065, 0.065]):
        name, data = BENCH_FRAMES[(i + 3) % 10]
        pay = bytearray(build_payload(data))
        pay[rnd.randrange(51)] ^= (1 << rnd.randrange(8))
        yield ("F%02d_%s_eps%+.3f" % (i, name, eps),
               cap_from_payload(bytes(pay), eps, phases[i % 5]))

    # G: the silicon operating mix (bench frames at real trim points)
    for i in range(20):
        name, data = BENCH_FRAMES[i % 10]
        eps = -0.0109 if i < 10 else 0.0008
        yield ("G%02d_%s_eps%+.4f" % (i, name, eps),
               cap_from_payload(build_payload(data), eps,
                                phases[(i * 3) % 5]))


def run_case(tag, raw, save_dir, port):
    U.gen_cap(raw)
    sym = U.build(True, True)
    sim = U.Ucsim(str(Path(U.__file__).parent / "sim_v2.ihx"), port)
    try:
        ticks, at_brk = sim.run_decode(brk=sym.get("_sim_done"), timeout=90.0)
        if not at_brk:
            # RUNAWAY: grab where it is before closing
            sim.cmd("stop", 0.3)
            st = sim.cmd("state", 0.4)
            return {"tag": tag, "runaway": True, "state": st,
                    "capture": raw.hex()}
        status = sim.read(sym["_g_status"], 1)[0]
        out = sim.read(sym["_g_out"], 48)
        di = sim.read(sym["_dec_info"], 20)
    finally:
        sim.close()
        sweep()
    d_c = bytes(out) if status != 0 else None
    d_py, ipy = v2.decode_ex(linearize(raw.hex()))
    rows = []
    if d_c != d_py:
        rows.append(("bytes", d_c.hex() if d_c else None,
                     d_py.hex() if d_py else None))
    if U.PATHS.get(di[0]) != ipy["path"]:
        rows.append(("path", U.PATHS.get(di[0]), ipy["path"]))
    if U.CAUSES.get(di[1]) != ipy["cause"]:
        rows.append(("cause", U.CAUSES.get(di[1]), ipy["cause"]))
    cvals = {"trials": di[2], "alias_cmp": di[3], "chased": di[4],
             "n_weak": (di[5] << 8) | di[6],
             "n_tied": (di[7] << 8) | di[8],
             "K": (di[9] << 8) | di[10],
             "violations": di[13],
             "infeasible": (di[14] << 8) | di[15],
             "label_err": (di[16] << 8) | di[17]}
    tau_c = (di[11] << 8) | di[12]
    if tau_c >= 0x8000:
        tau_c -= 0x10000
    cvals["tau"] = tau_c
    for f, cv in cvals.items():
        pv = ipy.get(f, 0)
        if pv is None:
            pv = 0
        if f == "chased":
            cv, pv = bool(cv), bool(pv)
        if cv != pv:
            rows.append((f, cv, pv))
    return {"tag": tag, "runaway": False,
            "ref": ipy["path"] or ipy["cause"],
            "ok": not rows, "rows": rows, "capture": raw.hex()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="ABCDEFG")
    ap.add_argument("--save-dir", default=str(HERE / "fuzz_out"))
    ap.add_argument("--start-port", type=int, default=21900)
    args = ap.parse_args()
    save = Path(args.save_dir)
    save.mkdir(exist_ok=True)

    cases = [(t, r) for (t, r) in gen_cases() if t[0] in args.only]
    print("fuzz48: %d cases (groups %s)" % (len(cases), args.only))
    n_ok = 0
    runaways = []
    mismatches = []
    results = []
    refhist = {}
    t0 = time.time()
    for n, (tag, raw) in enumerate(cases):
        res = run_case(tag, raw, save, args.start_port + (n % 50))
        results.append(res)
        if res["runaway"]:
            runaways.append(tag)
            (save / ("%s.cap" % tag)).write_text(res["capture"])
            print("%-30s -> RUNAWAY (crash reproduced) -- capture saved" % tag)
            continue
        refhist[res["ref"]] = refhist.get(res["ref"], 0) + 1
        if res["ok"]:
            n_ok += 1
            print("%-30s -> %-18s OK" % (tag, res["ref"]))
        else:
            mismatches.append(tag)
            print("%-30s -> %-18s MISMATCH %s" % (tag, res["ref"],
                                                  res["rows"]))
    dt = time.time() - t0
    print()
    print("reference outcome histogram:", json.dumps(refhist, indent=0))
    print("FUZZ48: %d/%d bit-identical, %d runaways, %d mismatches (%.0fs)"
          % (n_ok, len(cases), len(runaways), len(mismatches), dt))
    (save / "fuzz_results.json").write_text(json.dumps(results, indent=1))
    if runaways:
        print("RUNAWAY cases:", runaways)
    return 0 if (n_ok == len(cases)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
