#!/usr/bin/env python3
"""v2.2 synthetic fuzz corpus: decode_asm.s in ucsim vs the Python
reference, at BOTH v2.2 geometries -- production (ND_DATA=48, CHK_LEN=4,
60-byte frames = exactly 20 LEDs, 288-byte captures) and test (ND_DATA=16,
CHK_LEN=4, 28-byte frames, 256-byte captures).

Refusal/chase-biased like fuzz48.py, plus the majority shapes that are
NEW in v2.2's >=2-of-4 vote:
  * one corrupted check byte            -> 3-of-4 majority survives
  * two check bytes corrupted APART     -> the surviving pair still wins
                                           (v2.1 could not survive this)
  * two check bytes corrupted ALIKE     -> 2-2 TIE: no majority
  * three corrupted apart               -> full split: no majority

Case groups (production geometry unless marked T):
  A  eps corners (+/-3..7.5%) with clean payloads     -> emitgate/lock/...
  B  corrupted check blocks (singles, pairs, ties,
     splits, inversions)                              -> chase check phases
                                                         + majority shapes
  C  corrupted DATA wire bytes (1..2 flips)           -> chase data phases,
                                                         alias guard, R6-R8
  D  mid-frame trigger (capture starts at bit j > 0)  -> partial frames
  E  random bit noise in the PACKED capture bytes     -> scanner stress
  G  the 10 bench frames at this unit's real operating
     points (factory -1.09%, converged +0.08%)        -> the silicon mix
  T  the same mix at TEST geometry (ND=16, 28-B frames)

Every case runs in ucsim under the PRODUCTION-IDENTICAL link
(ucsim_bitexact.build with ASMDEC: --code-loc 0x8068, --data-loc 0x100,
vectors_sim.s, VGAP link guard) and is diffed bit-exactly against the
Python reference (bytes + path + cause + all counters).  A case that
never reaches _sim_done is a RUNAWAY; its capture is saved.

Simulator hygiene: ucsim_bitexact spawns every ucsim_stm8 child under
`setsid timeout -k 5 120` and runs a pkill/pgrep sweep on every close.

Usage: python3 fuzz_v22.py [--only GROUPS] [--save-dir DIR]
"""
import argparse
import json
import random
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
U.CHK = 4
v2 = U.v2

CAP_PROD = 288
CAP_TEST = 256


# ---- capture builders ---------------------------------------------------

def pack(samples, nbytes):
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


def cap_from_payload(payload, eps, phase, nbytes):
    return pack(synth_capture(payload, eps=eps, phase_ns=phase), nbytes)


def cap_from_wire(wire, eps, phase, nbytes, bit_off=0):
    bits = [int(b) for byte in wire for b in f"{byte:08b}"]
    return pack(_simulate(bits[bit_off:], eps, 0.0, phase, synth.N_ITER),
                nbytes)


def _lcg(seed, n):
    x, out = seed, bytearray()
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


# the 10 bench frames (bench/drive_prod.py FRAMES, verbatim data bytes)
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

# 16-byte test payloads for the T group
TEST_DATA = [
    ("zeros", bytes(16)),
    ("ones", bytes([0xFF] * 16)),
    ("count", bytes(range(16))),
    ("aa", bytes([0xAA] * 16)),
    ("rnd1", _lcg(1, 16)),
    ("rnd2", _lcg(2, 16)),
]

PHASES = [254.0, 330.0, 385.0, 440.0, 501.0]


def gen_prod_cases():
    """Yield (tag, raw_capture) at production geometry (ND=48, 288 B)."""
    rnd = random.Random(0xF22DEC)

    # A: eps corners, clean payloads (10)
    eps_pts = [-0.075, -0.06, -0.045, -0.03, 0.03, 0.045, 0.06, 0.075,
               -0.029, 0.029]
    for i, eps in enumerate(eps_pts):
        name, data = BENCH_FRAMES[i % 10]
        yield ("A%02d_%s_eps%+.3f" % (i, name, eps),
               cap_from_payload(build_payload(data), eps, PHASES[i % 5],
                                CAP_PROD))

    # B: corrupted check blocks -- the v2.2 majority shapes (14).
    # Check bytes sit at payload offsets 48..51.
    b_cases = [
        ("one0",   [(48, 0x01)]),               # single, byte 0 (3-of-4)
        ("one1",   [(49, 0x80)]),               # single, byte 1
        ("one2",   [(50, 0x10)]),               # single, byte 2
        ("one3",   [(51, 0x04)]),               # single, the NEW 4th byte
        ("inv0",   [(48, 0xFF)]),               # whole byte inverted
        ("apart2", [(48, 0x01), (49, 0x02)]),   # 2 apart: pair survives
        ("apart2b", [(50, 0x21), (51, 0x84)]),  # 2 apart, tail bytes
        ("tie01",  [(48, 0x01), (49, 0x01)]),   # 2 ALIKE: 2-2 tie
        ("tie13",  [(49, 0x40), (51, 0x40)]),   # tie, split positions
        ("tie02",  [(48, 0xFF), (50, 0xFF)]),   # tie by inversion
        ("wrongmaj", [(48, 0x03), (49, 0x03), (50, 0x03)]),  # 3 alike-wrong:
                                                # majority exists but WRONG
        ("split3", [(48, 0x01), (49, 0x02), (50, 0x04)]),    # full split
        ("split3b", [(49, 0x11), (50, 0x22), (51, 0x44)]),
        ("allbad", [(48, 0x0F), (49, 0xF0), (50, 0x3C), (51, 0xC3)]),
    ]
    eps_b = [0.0, -0.01072, 0.01274, -0.025, 0.0, -0.01072, 0.02,
             0.01274, 0.0, -0.025, 0.0, -0.01072, 0.008, 0.0]
    for i, (bt, flips) in enumerate(b_cases):
        name, data = BENCH_FRAMES[i % 10]
        pay = bytearray(build_payload(data))
        for off, mask in flips:
            pay[off] ^= mask
        yield ("B%02d_%s_%s" % (i, name, bt),
               cap_from_payload(bytes(pay), eps_b[i], PHASES[i % 5],
                                CAP_PROD))

    # C: corrupted DATA wire bytes (8)
    for i in range(8):
        name, data = BENCH_FRAMES[i]
        pay = bytearray(build_payload(data))
        pay[rnd.randrange(48)] ^= (1 << rnd.randrange(8))
        if i % 2:
            pay[rnd.randrange(48)] ^= (1 << rnd.randrange(8))
        yield ("C%02d_%s_data" % (i, name),
               cap_from_payload(bytes(pay), [-0.01072, 0.0, 0.008][i % 3],
                                PHASES[i % 5], CAP_PROD))

    # D: mid-frame trigger (6) -- frame is 480 bits now
    for i, boff in enumerate([40, 120, 240, 360, 460, 476]):
        name, data = BENCH_FRAMES[i % 10]
        wire = wire_frame(build_payload(data))
        yield ("D%02d_%s_bit%d" % (i, name, boff),
               cap_from_wire(wire, [-0.01072, 0.0][i % 2], PHASES[i % 5],
                             CAP_PROD, bit_off=boff))

    # E: random bit noise in the packed capture (6)
    for i, nflip in enumerate([1, 2, 4, 8, 12, 16]):
        name, data = BENCH_FRAMES[i % 10]
        raw = bytearray(cap_from_payload(build_payload(data),
                                         [-0.01072, 0.0][i % 2],
                                         PHASES[i % 5], CAP_PROD))
        for _ in range(nflip):
            raw[rnd.randrange(CAP_PROD)] ^= (1 << rnd.randrange(8))
        yield ("E%02d_%s_n%d" % (i, name, nflip), bytes(raw))

    # G: the silicon operating mix (8)
    for i in range(8):
        name, data = BENCH_FRAMES[i]
        eps = -0.0109 if i % 2 else 0.0008
        yield ("G%02d_%s_eps%+.4f" % (i, name, eps),
               cap_from_payload(build_payload(data), eps,
                                PHASES[(i * 3) % 5], CAP_PROD))


def gen_test_cases():
    """Yield (tag, raw_capture) at TEST geometry (ND=16, 28-B frames)."""
    rnd = random.Random(0x1622)
    # clean at eps corners (4)
    for i, eps in enumerate([-0.05, -0.011, 0.0008, 0.05]):
        name, data = TEST_DATA[i % 6]
        yield ("T%02d_%s_eps%+.3f" % (i, name, eps),
               cap_from_payload(build_payload(data), eps, PHASES[i % 5],
                                CAP_TEST))
    # check-block shapes at offsets 16..19 (6)
    t_cases = [
        ("one3",  [(19, 0x02)]),
        ("apart", [(16, 0x01), (18, 0x80)]),
        ("tie",   [(17, 0x20), (19, 0x20)]),
        ("split", [(16, 0x01), (17, 0x02), (18, 0x04)]),
        ("inv",   [(18, 0xFF)]),
        ("all4",  [(16, 0x0F), (17, 0xF0), (18, 0x3C), (19, 0xC3)]),
    ]
    for i, (bt, flips) in enumerate(t_cases):
        name, data = TEST_DATA[(i + 1) % 6]
        pay = bytearray(build_payload(data))
        for off, mask in flips:
            pay[off] ^= mask
        yield ("T%02d_%s_%s" % (i + 4, name, bt),
               cap_from_payload(bytes(pay), [-0.011, 0.0][i % 2],
                                PHASES[i % 5], CAP_TEST))
    # corrupted data (2) + packed noise (2)
    for i in range(2):
        name, data = TEST_DATA[i + 2]
        pay = bytearray(build_payload(data))
        pay[rnd.randrange(16)] ^= (1 << rnd.randrange(8))
        yield ("T%02d_%s_data" % (i + 10, name),
               cap_from_payload(bytes(pay), -0.011, PHASES[i % 5],
                                CAP_TEST))
    for i in range(2):
        name, data = TEST_DATA[i]
        raw = bytearray(cap_from_payload(build_payload(data), 0.0,
                                         PHASES[i % 5], CAP_TEST))
        for _ in range(4):
            raw[rnd.randrange(CAP_TEST)] ^= (1 << rnd.randrange(8))
        yield ("T%02d_%s_noise" % (i + 12, name), bytes(raw))


def run_case(tag, raw, save_dir, port, nd):
    U.gen_cap(raw)
    sym = U.build(True, True)
    sim = U.Ucsim(str(Path(U.__file__).parent / "sim_v2.ihx"), port)
    try:
        ticks, at_brk = sim.run_decode(brk=sym.get("_sim_done"), timeout=90.0)
        if not at_brk:
            sim.cmd("stop", 0.3)
            st = sim.cmd("state", 0.4)
            return {"tag": tag, "runaway": True, "state": st,
                    "capture": raw.hex()}
        status = sim.read(sym["_g_status"], 1)[0]
        out = sim.read(sym["_g_out"], nd)
        di = sim.read(sym["_dec_info"], 20)
    finally:
        sim.close()
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
    ap.add_argument("--only", default="ABCDEGT")
    ap.add_argument("--save-dir", default=str(HERE / "fuzz_v22_out"))
    ap.add_argument("--start-port", type=int, default=22300)
    args = ap.parse_args()
    save = Path(args.save_dir)
    save.mkdir(exist_ok=True)

    groups = [(48, [(t, r) for (t, r) in gen_prod_cases()
                    if t[0] in args.only]),
              (16, [(t, r) for (t, r) in gen_test_cases()
                    if t[0] in args.only])]
    total = sum(len(cs) for _, cs in groups)
    print("fuzz_v22: %d cases (groups %s; CHK_LEN=4, prod ND48 + test ND16)"
          % (total, args.only))
    n_ok = 0
    n = 0
    runaways = []
    mismatches = []
    results = []
    refhist = {}
    t0 = time.time()
    for nd, cases in groups:
        if not cases:
            continue
        U.ND_DATA = nd
        v2._configure(nd, check=True, chk=4)
        print("--- geometry ND_DATA=%d (frame %d B) ---" % (nd, nd + 12))
        for (tag, raw) in cases:
            res = run_case(tag, raw, save, args.start_port + (n % 50), nd)
            n += 1
            results.append(res)
            if res["runaway"]:
                runaways.append(tag)
                (save / ("%s.cap" % tag)).write_text(res["capture"])
                print("%-30s -> RUNAWAY -- capture saved" % tag)
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
    print("FUZZ_V22: %d/%d bit-identical, %d runaways, %d mismatches (%.0fs)"
          % (n_ok, total, len(runaways), len(mismatches), dt))
    (save / "fuzz_v22_results.json").write_text(json.dumps(results, indent=1))
    if runaways:
        print("RUNAWAY cases:", runaways)
    return 0 if (n_ok == total) else 1


if __name__ == "__main__":
    raise SystemExit(main())
