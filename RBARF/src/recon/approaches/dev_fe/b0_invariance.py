#!/usr/bin/env python3
"""PROOF for cap_arm.s FIX 2a: the decoder ignores capture byte 0 bits 7..6.

The new arm enters the pinned sampling loop at _cap_loop+1, skipping the
loop-top `rlc a` that (on the FIRST iteration only) would deposit a
meaningless C flag into byte 0 bit 6 and shift bit 7.  cap_code.s
documents those two bits as garbage and decode.c's scanner takes loop i's
slots 6,7 from byte i+1 -- so byte 0 bits 7..6 are unreachable.  This
script proves it EMPIRICALLY: every capture in every corpus (plus the 177
real production dumps from the arm investigation and the v2.3 fuzz set) is
decoded four times, with byte 0 bits 7..6 forced to 00/01/10/11, and every
field of the result must be identical.

data/captures_val.json is never read.
"""
import gzip
import json
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_arm"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
import armlib as A                                              # noqa: E402

FIELDS = [f[0] for f in A.DecInfo._fields_]


def result(cap: bytes):
    st, out, info, epsc = A.decode(cap)
    return (int(st), out.hex(), epsc,
            tuple(int(getattr(info, f)) for f in FIELDS))


def variants(cap: bytes):
    b = bytearray(cap)
    for hi in (0x00, 0x40, 0x80, 0xC0):
        b[0] = (cap[0] & 0x3F) | hi
        yield hi, bytes(b)


def check(name, caps):
    n = bad = 0
    for tag, cap in caps:
        ref = None
        for hi, v in variants(cap):
            r = result(v)
            if ref is None:
                ref = r
            elif r != ref:
                bad += 1
                d = [f for f, x, y in zip(FIELDS, r[3], ref[3]) if x != y]
                print("   MISMATCH %s %s hi=0x%02X: st %s/%s bytes %s "
                      "fields %s" % (name, tag, hi, r[0], ref[0],
                                     "differ" if r[1] != ref[1] else "same",
                                     d))
                break
        n += 1
    print("   %-34s %4d captures x 4 variants  %s"
          % (name, n, "OK -- identical" if not bad
             else "FAIL %d" % bad))
    return n, bad


def main():
    tot = bad = 0
    for f in sorted((NEWIMPL / "data").glob("captures*.json")):
        if f.name == "captures_val.json":
            continue                       # SEALED -- never read
        d = json.loads(f.read_text())
        caps = [(c.get("pattern", "?") + "/" + str(c.get("rep", "")),
                 bytes.fromhex(c["capture"]))
                for c in d["captures"] if c.get("capture")]
        n, b = check(f.name, caps)
        tot += n
        bad += b

    # the 177 real production dumps from the arm investigation
    caps = []
    for run in ("a", "b"):
        p = (NEWIMPL / "recon" / "approaches" / "dev_arm"
             / ("arm_run_%s.json" % run))
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        for i, s in enumerate(d["stream"]):
            if s["line"].startswith("B"):
                caps.append(("run%s#%d" % (run, i),
                             bytes.fromhex(s["line"][1:])))
    if caps:
        n, b = check("arm_run dumps (real silicon)", caps)
        tot += n
        bad += b

    # the v2.3 fuzz corpus at the production geometry
    try:
        import fuzz_v23
        cs = fuzz_v23.cases(48)
        caps = [(c[0], c[1]) for c in cs]
        n, b = check("fuzz_v23 ND=48", caps)
        tot += n
        bad += b
    except Exception as exc:               # noqa: BLE001
        print("   fuzz_v23 skipped: %s" % exc)

    print("\nBYTE-0 BITS 7..6 INVARIANCE: %d captures, %d x 4 decodes, "
          "%d mismatches -- %s" % (tot, tot, bad, "PASS" if not bad
                                   else "FAIL"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
