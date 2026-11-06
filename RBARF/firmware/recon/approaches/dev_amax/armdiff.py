#!/usr/bin/env python3
"""The pinned-block proof for a chase-budget bench image.

A bigger A_MAX grows the candidate arrays, which are REL DATA, which
pushes every DATA symbol linked after them up by 3 B per entry -- and
cap_arm.s's `s_arm` counter is one of them.  So the CAPARM block cannot
be byte-identical, and this script proves the ONLY thing that changed is
the four `s_arm` OPERAND bytes, exactly the discipline cap_arm.s's own
header states for the SS16.3 diagnostic arm ("differs from this arm in
exactly the 4 s_arm operand bytes, all four polls byte-identical").

What is asserted, per image, against the baseline image:
  * CAPLOOP 0x9FA1..0x9FF0 and 0x9FF1..0x9FFF byte-identical (HARD PINS);
  * every differing byte in 0x9F63..0x9FFF is the low half of an s_arm
    operand -- i.e. it sits at one of the 4 known offsets AND its value
    equals baseline + 3*(A_MAX - 11);
  * the four edge-detect BTJT polls (72 06 50 0B + rel) byte-identical,
    so the calibrated poll comb is untouched;
  * _cap_arm still at 0x9F63 and _cap_loop at 0x9FAF in both maps.

  python3 armdiff.py <baseline.ihx> <image.ihx>:<A_MAX> [...]
INVESTIGATION-ONLY: reads .ihx/.map, writes nothing.
"""
import re
import sys
from pathlib import Path

CAPARM, CAPARM_END = 0x9F63, 0x9FFF
HARD = ((0x9FA1, 0x9FF0), (0x9FF1, 0x9FFF))
# the four s_arm operand LOW bytes, measured in the linked baseline:
#   mov s_arm,#8 @0x9F63 -> 0x9F66;  mov s_arm,#7 @0x9F71 -> 0x9F74
#   dec s_arm    @0x9F8F -> 0x9F92;  dec s_arm    @0x9F97 -> 0x9F9A
S_ARM_LO = (0x9F66, 0x9F74, 0x9F92, 0x9F9A)
A_MAX_BASE = 11
POLL = b"\x72\x06\x50\x0b"


def load(p):
    mem = {}
    for line in open(p):
        line = line.strip()
        if not line.startswith(":"):
            continue
        n = int(line[1:3], 16)
        a = int(line[3:7], 16)
        if int(line[7:9], 16) == 0:
            for i, b in enumerate(bytes.fromhex(line[9:9 + 2 * n])):
                mem[a + i] = b
    return mem


def blk(m, lo, hi):
    return bytes(m.get(a, 0xFF) for a in range(lo, hi + 1))


def polls(m):
    out = []
    for a in range(CAPARM, 0x9FA1 - 4):
        if blk(m, a, a + 3) == POLL:
            out.append((a, m.get(a + 4, 0)))
    return out


def main(argv):
    base = load(argv[0])
    rc = 0
    for spec in argv[1:]:
        path, amax = spec.rsplit(":", 1)
        amax = int(amax)
        m = load(path)
        errs = []
        for lo, hi in HARD:
            if blk(m, lo, hi) != blk(base, lo, hi):
                errs.append("HARD PIN 0x%X..0x%X DIFFERS" % (lo, hi))
        delta = 3 * (amax - A_MAX_BASE)
        diffs = [a for a in range(CAPARM, CAPARM_END + 1)
                 if m.get(a, 0xFF) != base.get(a, 0xFF)]
        for a in diffs:
            if a not in S_ARM_LO:
                errs.append("byte 0x%X differs and is NOT an s_arm operand "
                            "(0x%02X -> 0x%02X)"
                            % (a, base.get(a, 0xFF), m.get(a, 0xFF)))
            elif (m[a] - base[a]) % 256 != delta % 256:
                errs.append("s_arm operand 0x%X moved by %+d, expected "
                            "%+d for A_MAX %d"
                            % (a, m[a] - base[a], delta, amax))
        if delta and sorted(diffs) != list(S_ARM_LO):
            errs.append("expected all 4 s_arm operands to move, got %s"
                        % [hex(a) for a in diffs])
        if not delta and diffs:
            errs.append("A_MAX == baseline but %d bytes differ" % len(diffs))
        pb, pm = polls(base), polls(m)
        if pb != pm:
            errs.append("BTJT poll comb changed: %s -> %s" % (pb, pm))
        mp = Path(path[:-4] + ".map")
        if mp.is_file():
            t = mp.read_text()
            for nm, want in (("_cap_arm", 0x9F63), ("_cap_loop", 0x9FAF)):
                g = re.search(r"([0-9A-F]{8})\s+%s\b" % nm, t)
                if not g or int(g.group(1), 16) != want:
                    errs.append("%s != 0x%X in the map" % (nm, want))
        print("%s  (A_MAX %d, s_arm expected +%d B)" % (path, amax, delta))
        print("   CAPLOOP hard pins: %s"
              % ("OK, byte-identical" if not any("HARD" in e for e in errs)
                 else "FAIL"))
        print("   CAPARM 0x9F63..0x9FFF differing bytes: %d %s"
              % (len(diffs), [hex(a) for a in diffs]))
        print("   4 edge-detect BTJT polls: %s"
              % ("byte-identical" if pb == pm else "CHANGED"))
        if errs:
            rc = 1
            for e in errs:
                print("   FAIL: " + e)
        else:
            print("   VERDICT: the ONLY change above 0x9F63 is the four "
                  "s_arm operand bytes, each +%d" % delta)
    print("ARMDIFF:", "PASS" if rc == 0 else "FAIL")
    return rc


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv[1:]))
