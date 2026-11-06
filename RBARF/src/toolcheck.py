#!/usr/bin/env python3
"""Fail the build LOUDLY on a toolchain that is not the one the shipping
images were produced with.

SDCC's code generator is not stable across releases: a different SDCC
silently produces a different, still-working image -- which quietly
invalidates every byte-level claim in recon/PROD_CLOSURE.md (the flash
ledger, the pinned-CAPLOOP md5s, guard_prod.py's address-phase pins) and
the three ledger md5s in README.md.  This check is the difference between
"the build changed" and "we found out six months later".

Pinned toolchain (produced build/rbarf_prod.ihx 32e8057d..., 
build/rbarf_prod_verbose.ihx 6871bd7e..., build/capture.ihx 84955f77...):

    sdcc      4.6.0
    sdasstm8  V05.50.4   (sdas assembler, STM8)
    sdld      V05.50.4

Escape hatch, for deliberate experiments only:

    make RBARF_SKIP_TOOLCHECK=1 ...      # or export RBARF_SKIP_TOOLCHECK=1

which prints a warning and proceeds.  An image built that way is NOT a
ledger image: do not flash it and do not quote its md5.

Usage: toolcheck.py [--quiet]
"""
import os
import re
import subprocess
import sys

# (tool, argv, regex capturing the version, expected)
PINNED = [
    ("sdcc",     ["sdcc", "--version"],     r"\b(\d+\.\d+\.\d+)\b(?=\s*#)", "4.6.0"),
    ("sdasstm8", ["sdasstm8", "-v"],        r"sdas Assembler V(\d+\.\d+\.\d+)", "05.50.4"),
    ("sdld",     ["sdld", "-v"],            r"sdld Linker V(\d+\.\d+\.\d+)",    "05.50.4"),
]


def _run(argv):
    """Version banners go to stdout or stderr and may exit non-zero."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        return None
    except OSError as e:
        return "OSError: %s" % e
    return (r.stdout or "") + (r.stderr or "")


def main(argv):
    quiet = "--quiet" in argv
    if os.environ.get("RBARF_SKIP_TOOLCHECK"):
        print("toolcheck: SKIPPED (RBARF_SKIP_TOOLCHECK set) -- the images "
              "this build produces are NOT ledger images", file=sys.stderr)
        return 0

    problems, seen = [], []
    for name, cmd, rx, want in PINNED:
        out = _run(cmd)
        if out is None:
            problems.append("%s: not found on PATH" % name)
            continue
        m = re.search(rx, out)
        if not m:
            problems.append("%s: could not parse a version from %r"
                            % (name, out.strip().splitlines()[:1]))
            continue
        got = m.group(1)
        seen.append("%s %s" % (name, got))
        if got != want:
            problems.append("%s is %s, the images were built with %s"
                            % (name, got, want))

    if problems:
        print("=" * 70, file=sys.stderr)
        print("TOOLCHAIN MISMATCH -- refusing to build.", file=sys.stderr)
        for p in problems:
            print("  * " + p, file=sys.stderr)
        print("", file=sys.stderr)
        print("  This toolchain will not reproduce the shipping images "
              "byte-for-byte;", file=sys.stderr)
        print("  SDCC codegen changes between releases.  The ledger md5s in",
              file=sys.stderr)
        print("  README.md and recon/PROD_CLOSURE.md are only meaningful "
              "under the", file=sys.stderr)
        print("  pinned toolchain (see toolcheck.py).", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Install the pinned versions, or -- for a deliberate "
              "experiment only --", file=sys.stderr)
        print("      make RBARF_SKIP_TOOLCHECK=1 <target>", file=sys.stderr)
        print("  which produces a NON-LEDGER image.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return 1

    if not quiet:
        print("toolcheck: " + ", ".join(seen) + "  (pinned, ledger-capable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
