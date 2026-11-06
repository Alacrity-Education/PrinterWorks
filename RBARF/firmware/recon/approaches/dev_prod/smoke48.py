#!/usr/bin/env python3
"""Task-5 smoke: PRODUCTION-GEOMETRY (ND_DATA=48, 60-byte v2.2
frames, 288-byte capture buffer) decode of 10 synthetic captures in
ucsim, bit-exact against the Python reference at _configure(48).

Synthetic captures come from recon/synth.py (the fitted sampler model,
99.96% agreement with real silicon) at a spread of clock-error points --
strong-band deliveries AND corner refusals both count: the contract is
that the STM8 image and the reference agree on bytes + path + cause +
counters for every frame.

Every ucsim invocation is timeout-guarded by the caller (run under
`timeout -k`); the Ucsim class kills its child on close.
"""
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

U.ASMDEC = True
U.ND_DATA = 48
v2 = U.v2
v2._configure(48, check=True)

CAP_BYTES = 288                           # production buffer (spec SS3)


def pack(samples, nbytes):
    """Inverse of harness.linearize: (i, s, level) triples -> raw capture
    bytes in the cap_code.s layout (byte i bits5..0 = R0..R5 of loop i,
    bits7..6 = BS0/BS1 of loop i-1; byte 0's top bits are don't-care)."""
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


def payloads():
    import random
    rnd = random.Random(0xB00F)
    ps = []
    ps.append(bytes((i * 5) & 0xFF for i in range(48)))     # spec SS2.4 vector
    ps.append(bytes(48))                                    # zeros
    ps.append(bytes([0xFF] * 48))                           # ones
    ps.append(bytes([0xAA] * 48))                           # alternating
    ps.append(bytes(rnd.randrange(256) for _ in range(48))) # random GRB
    ps.append(bytes([0, 64, 0] * 8 + [1, 40, 0, 0, 0, 64] + [0] * 18))
    return ps


CASES = [  # (payload idx, eps, phase_ns)
    (0,  0.0,     300.0),
    (1, -0.01072, 254.0),      # factory trim point
    (2,  0.01274, 480.0),      # trim 6
    (3, -0.01,    501.0),
    (4,  0.0,     385.0),
    (5, -0.02248, 330.0),      # trim 1
    (4,  0.01,    420.0),
    (0, -0.025,   275.0),      # strong-band edge
    (4,  0.075,   380.0),      # corner: expect refusal, still bit-exact
    (2, -0.075,   310.0),      # corner: expect refusal, still bit-exact
]


def main():
    pls = payloads()
    n_ok = 0
    results = []
    for n, (pi, eps, ph) in enumerate(CASES):
        payload = build_payload(pls[pi])          # DATA + CRC8 x4 (52 B)
        assert len(payload) == 52   # v2.2: DATA + CRC8 x4
        samples = synth_capture(payload, eps=eps, phase_ns=ph)
        raw = pack(samples, CAP_BYTES)
        U.gen_cap(raw)
        sym = U.build(True, True)
        sim = U.Ucsim(str(Path(U.__file__).parent / "sim_v2.ihx"), 21700 + n)
        try:
            _, at_brk = sim.run_decode(brk=sym.get("_sim_done"))
            status = sim.read(sym["_g_status"], 1)[0]
            out = sim.read(sym["_g_out"], 48)
            di = sim.read(sym["_dec_info"], 20)
        finally:
            sim.close()
        if not at_brk:
            print("case%02d RUNAWAY: never reached sim_done -> FAIL" % n)
            results.append(("case%02d" % n, "runaway", False, []))
            continue
        d_c = bytes(out) if status != 0 else None
        from harness import linearize
        d_py, ipy = v2.decode_ex(linearize(raw.hex()))
        rows = []
        if d_c != d_py:
            rows.append(("bytes", d_c.hex() if d_c else None,
                         d_py.hex() if d_py else None))
        if U.PATHS.get(di[0]) != ipy["path"]:
            rows.append(("path", U.PATHS.get(di[0]), ipy["path"]))
        if U.CAUSES.get(di[1]) != ipy["cause"]:
            rows.append(("cause", U.CAUSES.get(di[1]), ipy["cause"]))
        for f, cv in (("trials", di[2]), ("alias_cmp", di[3]),
                      ("n_weak", (di[5] << 8) | di[6]),
                      ("n_tied", (di[7] << 8) | di[8]),
                      ("K", (di[9] << 8) | di[10])):
            pv = ipy.get(f, 0) or 0
            if cv != pv:
                rows.append((f, cv, pv))
        ok = not rows
        n_ok += ok
        tag = "case%02d p%d eps=%+.3f%%" % (n, pi, eps * 100)
        results.append((tag, ipy["path"] or ipy["cause"], ok, rows))
        print("%-28s -> %-18s %s %s" %
              (tag, ipy["path"] or ipy["cause"], "OK" if ok else "MISMATCH",
               rows if rows else ""))
        # correctness of delivered payloads vs ground truth (extra check:
        # a delivery must equal the sent DATA -- catastrophic detector)
        if d_py is not None and d_py != pls[pi]:
            print("    !! CATASTROPHIC vs ground truth"); n_ok -= 1
    print("ND48 SMOKE: %d/%d bit-identical -> %s"
          % (n_ok, len(CASES), "PASS" if n_ok == len(CASES) else "FAIL"))
    return 0 if n_ok == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
