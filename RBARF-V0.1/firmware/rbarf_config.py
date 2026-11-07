#!/usr/bin/env python3
"""Repo-local configuration: external paths, the probe port, and toolchain
lookup.  Import this instead of hardcoding anything machine-specific.

Nothing here touches the firmware, the decoder or any bench constant --
it only answers "where does this host keep X", so the tree works on a
different machine and for a different user.

Environment overrides (all optional; the defaults are the values the
shipping images were produced and bench-proved with):

  RBARF_PICOTOOL_HOST   directory holding the RP2040 probe library
                        (testprobe.py).  Default:
                        /home/alex.lucaci/Projects/picotool/host
  RBARF_PROBE_PORT      serial device of the RP2040 probe.  Default:
                        glob /dev/serial/by-id/usb-Raspberry_Pi_Pico_*
                        then /dev/ttyACM0
  RBARF_STM8FLASH       stm8flash binary.        Default: PATH lookup
  RBARF_UCSIM           ucsim_stm8 binary.       Default: PATH lookup
  RBARF_SDCC            sdcc binary.             Default: PATH lookup
  RBARF_SDAS            sdasstm8 binary.         Default: PATH lookup

Typical use in a bench script (depth-independent bootstrap):

    import sys
    from pathlib import Path
    sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                                if (p / "rbarf_config.py").is_file())))
    from rbarf_config import picotool_host
    sys.path.insert(0, picotool_host())
    from testprobe import TestProbe
"""
import glob
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# The bench this project was developed and proved on.  Documented default,
# not a requirement -- override with RBARF_PICOTOOL_HOST.
DEFAULT_PICOTOOL_HOST = "/home/alex.lucaci/Projects/picotool/host"
DEFAULT_PROBE_GLOB = "/dev/serial/by-id/usb-Raspberry_Pi_Pico_*"
DEFAULT_PROBE_FALLBACK = "/dev/ttyACM0"


def _die(msg):
    raise SystemExit("[rbarf-config] " + msg)


def picotool_host(required=True):
    """Directory holding the RP2040 probe library (testprobe.py).

    Returns the path as a str so it can go straight into sys.path.
    Fails with a one-line explanation rather than an ImportError
    traceback when the library is not installed or not configured.
    """
    p = os.environ.get("RBARF_PICOTOOL_HOST", DEFAULT_PICOTOOL_HOST)
    if not required:
        return p
    if not os.path.isdir(p):
        _die("probe library directory not found: %r\n"
             "  This tree needs the RP2040 test-probe host library.\n"
             "  Set RBARF_PICOTOOL_HOST to the 'host' directory of your\n"
             "  picotool checkout, e.g.\n"
             "    export RBARF_PICOTOOL_HOST=~/Projects/picotool/host" % p)
    # picotool ships `testprobe` as a PACKAGE (host/testprobe/__init__.py);
    # accept a plain module too, in case a checkout flattens it.
    if not (os.path.isfile(os.path.join(p, "testprobe.py"))
            or os.path.isfile(os.path.join(p, "testprobe", "__init__.py"))):
        _die("no importable `testprobe` in %r\n"
             "  RBARF_PICOTOOL_HOST must point at the directory that CONTAINS\n"
             "  the testprobe package or module (picotool's 'host' directory)."
             % p)
    return p


def import_testprobe():
    """sys.path-insert the probe library and return its TestProbe class."""
    p = picotool_host()
    if p not in sys.path:
        sys.path.insert(0, p)
    try:
        from testprobe import TestProbe
    except ImportError as e:                       # pragma: no cover
        _die("probe library at %r is not importable: %s" % (p, e))
    return TestProbe


def probe_port(explicit=None, required=False):
    """Serial device of the RP2040 probe.

    Order: explicit argument, RBARF_PROBE_PORT, glob discovery, then the
    documented /dev/ttyACM0 fallback.  With required=True a missing probe
    is a clear error instead of a confusing open() failure later.
    """
    if explicit:
        return explicit
    env = os.environ.get("RBARF_PROBE_PORT")
    if env:
        return env
    hits = sorted(glob.glob(os.environ.get("RBARF_PROBE_GLOB",
                                           DEFAULT_PROBE_GLOB)))
    if hits:
        return hits[0]
    if required:
        _die("no RP2040 probe found (glob %r) and RBARF_PROBE_PORT is not\n"
             "  set.  Plug the probe in, or set RBARF_PROBE_PORT=/dev/..."
             % DEFAULT_PROBE_GLOB)
    return DEFAULT_PROBE_FALLBACK


def require_tool(name, env_var=None, hint=""):
    """Absolute path to an external tool, or a clear 'not installed' error."""
    env_var = env_var or ("RBARF_" + name.upper().replace("-", "_"))
    p = os.environ.get(env_var)
    if p:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
        _die("%s=%r is not an executable file" % (env_var, p))
    p = shutil.which(name)
    if p:
        return p
    _die("%s not found on PATH%s\n"
         "  Install it, or set %s to its full path."
         % (name, ("\n  " + hint) if hint else "", env_var))


def stm8flash():
    return require_tool("stm8flash", "RBARF_STM8FLASH",
                        "hint: https://github.com/vdudouyt/stm8flash")


def ucsim():
    return require_tool("ucsim_stm8", "RBARF_UCSIM",
                        "hint: ships with SDCC as 'ucsim_stm8' (sdcc-ucsim)")


def sdcc():
    return require_tool("sdcc", "RBARF_SDCC")


def sdas():
    return require_tool("sdasstm8", "RBARF_SDAS")


if __name__ == "__main__":
    print("PROJECT_ROOT       ", PROJECT_ROOT)
    print("picotool host      ", picotool_host(required=False),
          "(present)" if os.path.isdir(picotool_host(required=False))
          else "(MISSING -- set RBARF_PICOTOOL_HOST)")
    print("probe port         ", probe_port())
    for fn, nm in ((stm8flash, "stm8flash"), (ucsim, "ucsim_stm8"),
                   (sdcc, "sdcc"), (sdas, "sdasstm8")):
        try:
            print("%-19s %s" % (nm, fn()))
        except SystemExit as e:
            print("%-19s NOT AVAILABLE" % nm)
