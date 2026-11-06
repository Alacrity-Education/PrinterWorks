#!/usr/bin/env python3
"""Legacy link guard for the SUPERSEDED v2.1 bench images.

This is NOT the production guard -- that is guard_prod.py, which is
stricter and is the one that gates every shipping link.  This one only
checks what the v2.1 links can still be checked for: that REL CODE does
not run into the ABS capture loop, and that the loop keeps its
calibrated address phase.

Why it exists: `make rbarf-v21` carried this check inline; its sibling
`make rbarf-v21-trim` carried NO check at all and so linked a silently
CORRUPT image (CODE overwriting the pinned loop).  Both use this now.

Usage: guard_caploop.py <mapfile>
"""
import re
import sys

EXPLAIN = """
  Why this happens at HEAD: the v2.1 targets link the CURRENT decode.c,
  which has since grown into the v2.3 decoder (CRC-16 chase, 3+3 markers,
  the wider reference cross product).  Even at V21FLAGS geometry it no
  longer fits underneath caploop.s's pinned `.org 0x9FA1`.

  This is EXPECTED and is not a regression in the shipping build.  The
  v2.1 images are historical: to rebuild one you also need a v2.1-era
  decode.c, which is not kept in this tree.  Do NOT "fix" this by moving
  the capture loop -- its flash address PHASE is calibrated and pinned
  (recon/PROD_CLOSURE.md SS2, guard_prod.py).  See archive/README.md.
"""


def main(path):
    m = open(path).read()
    code = re.search(r"CODE\s+([0-9A-F]{8})\s+([0-9A-F]{8})", m)
    cap = re.search(r"([0-9A-F]{8})\s+_cap_capture", m)
    if not code or not cap:
        print("guard_caploop: CODE or _cap_capture missing from %s" % path)
        return 1
    end = int(code.group(1), 16) + int(code.group(2), 16)
    cap = int(cap.group(1), 16)
    if end > cap:
        print("LEGACY GUARD FAIL (%s):" % path)
        print("  OVERLAP: CODE ends 0x%X, the pinned capture loop starts "
              "at 0x%X" % (end, cap))
        print("  the linked image is CORRUPT -- do not flash it.")
        print(EXPLAIN)
        return 1
    if (cap - 0x8111) % 16:
        print("LEGACY GUARD FAIL (%s):" % path)
        print("  ALIGN: _cap_capture 0x%X !~ 0x8111 mod 16 (phase broken)"
              % cap)
        return 1
    print("caploop guard OK: CODE end 0x%X <= _cap_capture 0x%X "
          "(phase 0x%X mod 16)" % (end, cap, cap % 16))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
