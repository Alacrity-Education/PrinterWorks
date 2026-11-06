#!/usr/bin/env python3
"""Replay the two HISTORICAL CATASTROPHIC frames under v2.3.

Both were emitted on 2026-09-07 by the v2.2 chase at eps +0.23 % / +0.26 %
(PROD_CLOSURE SS11.4): an UNDETECTABLE weight-4 CRC-8 codeword on a
>= 96-bit all-zero run.  This replays the SAME 48 DATA bytes through the
v2.3 wire and decoder over the recorded operating points and the whole
measured arm-phase spread, and reports every emission as correct or wrong.

The v2.2 emissions themselves are also re-tested directly: is the exact
4-bit error pattern the v2.2 chase accepted still undetectable at 16 bits?
"""
import sys
import json
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
sys.path.insert(0, str(SC.parents[2] / "bench"))
import v23lib as L                                              # noqa: E402
from crc import crc16_ccitt_false as c16, crc8_smbus as c8      # noqa: E402

KL = json.loads((SC.parents[2] / "klipper" /
                 "bench_klipper_macro_results.prefix_baseline.json").read_text())
CATS = [(r["case"], bytes.fromhex(r["truth"]), bytes.fromhex(r["decoded"]),
         r["eps_centi"])
        for r in KL["rows"] if r["verdict"] == "CATASTROPHIC"]

T0 = [375.0 + i * (736.0 - 375.0) / 11 for i in range(12)]
EPS = [round(-0.020 + i * 0.0005, 6) for i in range(101)]   # -2.0 .. +3.0 %


def main():
    print("=== the two recorded v2.2 wrong emissions, as ERROR PATTERNS ===")
    for (name, truth, wrong, epsc) in CATS:
        err = bytes(a ^ b for a, b in zip(truth, wrong))
        w = sum(bin(x).count("1") for x in err)
        print("%-16s eps %+d cc  weight-%d error" % (name, epsc, w))
        print("   CRC8  truth %02X  emitted %02X  -> %s"
              % (c8(truth), c8(wrong),
                 "UNDETECTED (this is why it shipped)"
                 if c8(truth) == c8(wrong) else "detected"))
        print("   CRC16 truth %04X  emitted %04X  -> %s"
              % (c16(truth), c16(wrong),
                 "UNDETECTED" if c16(truth) == c16(wrong)
                 else "DETECTED -- v2.3 would refuse this exact pattern"))
    print()
    print("=== the same payloads on the v2.3 wire, decoded by v2.3 ===")
    ev = L.load_ref()
    ev._configure(48, chk=6)
    tot = [0, 0, 0]
    for (name, truth, _wrong, epsc) in CATS:
        n = em = wr = 0
        at_rec = []
        for eps in EPS:
            for t0 in T0:
                out, info = ev.decode_ex(
                    L.linearize(L.capture(truth, eps, t0)))
                n += 1
                if out is not None:
                    em += 1
                    if out != truth:
                        wr += 1
                if abs(eps * 10000 - epsc) < 3:
                    at_rec.append((out is not None, out == truth
                                   if out is not None else None))
        print("%-16s %4d decodes, %4d emitted, %d WRONG" % (name, n, em, wr))
        print("                 at the RECORDED operating point (eps %+d cc, "
              "all 12 arm phases): %d emitted, %d correct"
              % (epsc, sum(1 for a, b in at_rec if a),
                 sum(1 for a, b in at_rec if b)))
        tot[0] += n
        tot[1] += em
        tot[2] += wr
    print("TOTAL replay: %d decodes, %d emissions, %d WRONG -> %.4f %%"
          % (tot[0], tot[1], tot[2],
             100.0 * tot[2] / tot[1] if tot[1] else 0.0))


if __name__ == "__main__":
    main()
