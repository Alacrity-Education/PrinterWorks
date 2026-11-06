#!/usr/bin/env python3
"""Extract the pinned ABS blocks from a linked .ihx and md5 them.

Ledger (PROD_CLOSURE.md SS15.0; CAPARM updated by SS16, re-phased by SS17):
  CAPLOOP0 0x9FA1..0x9FF0  273e269f41527530fd4a0261eb70f8a0   HARD PIN
  0x9FF1..0x9FFF           9ddd02276e5c30436e3b530eba05ad6a   HARD PIN
  0x9F63..0x9F9E           df991ffd34ca304daaa46ce864aea155   informational
                           (CURRENT arm: CAPARM_ORG 0x9F63, 60 B -- the arm
                            proper, SS17 comb-phase re-phasing)
  0x9F63..0x9FFF           964dcb4d5320fa362b80055eb20e0c5b   informational
                           (CURRENT arm + the 2-byte 0xFF gap + CAPLOOP)
  0x9F65..0x9FFF           1ebfc7b3a8a0b567dbd6b07486228e47   informational
                           (the SS16 arm at 0x9F65, kept for diffing)
  0x9F66..0x9FFF           c90a5bf952912e6c04606dc3c85290dc   informational
                           (the PRE-SS16 arm, kept for diffing)
Only the two CAPLOOP ranges make this script exit non-zero: the CAPARM
ranges are expected to differ whenever the arm changes (SS14/SS16/SS17),
and a diagnostic image differs from the shipping one in the s_arm operand
bytes.  The two historical rows (0x9F65, 0x9F66) therefore ALWAYS report
DIFF against a current image -- that is their purpose.
INVESTIGATION-ONLY: reads .ihx files, writes nothing.
"""
import hashlib
import sys

LEDGER = {
    (0x9FA1, 0x9FF0): "273e269f41527530fd4a0261eb70f8a0",
    (0x9FF1, 0x9FFF): "9ddd02276e5c30436e3b530eba05ad6a",
    (0x9F63, 0x9F9E): "df991ffd34ca304daaa46ce864aea155",
    (0x9F63, 0x9FFF): "964dcb4d5320fa362b80055eb20e0c5b",
    (0x9F65, 0x9FFF): "1ebfc7b3a8a0b567dbd6b07486228e47",
    (0x9F66, 0x9FFF): "c90a5bf952912e6c04606dc3c85290dc",
}
# ranges whose mismatch is informational, not a failure (see the docstring)
SOFT = {(0x9F63, 0x9F9E), (0x9F63, 0x9FFF),
        (0x9F65, 0x9FFF), (0x9F66, 0x9FFF)}


def load_ihx(path):
    mem = {}
    for line in open(path):
        line = line.strip()
        if not line.startswith(":"):
            continue
        n = int(line[1:3], 16)
        addr = int(line[3:7], 16)
        typ = int(line[7:9], 16)
        if typ == 0:
            for i, b in enumerate(bytes.fromhex(line[9:9 + 2 * n])):
                mem[addr + i] = b
    return mem


def blk(mem, lo, hi):
    return bytes(mem.get(a, 0xFF) for a in range(lo, hi + 1))


def main(paths):
    ref = None
    rc = 0
    for p in paths:
        mem = load_ihx(p)
        print(p)
        for (lo, hi), want in LEDGER.items():
            b = blk(mem, lo, hi)
            got = hashlib.md5(b).hexdigest()
            ok = "OK " if got == want else "DIFF"
            if got != want and (lo, hi) not in SOFT:
                rc = 1
            print("  0x%04X..0x%04X  %s  %s  (ledger %s)"
                  % (lo, hi, got, ok, want))
        if ref is None:
            ref = mem
        else:
            d = [a for a in range(0x9F63, 0x10000)
                 if ref.get(a) != mem.get(a)]
            print("  differing bytes 0x9F63..0xFFFF vs first image: %d %s"
                  % (len(d), ["0x%04X" % a for a in d[:12]]))
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
