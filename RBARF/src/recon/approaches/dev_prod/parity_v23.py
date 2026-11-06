#!/usr/bin/env python3
"""v2.3 host bit-exactness harness: decode.c (gcc, ctypes) vs
recon/approaches/embedded_v2.py, across every wire mode and geometry.

Diffed contract (spec B1), per capture:
    emitted bytes | refusal      (byte-identical)
    path label    (direct / chase / legacy_unverified / None)
    refusal cause (R1..R8 label)
    trials, alias_cmp, comps, n_refs, ref_split,
    n_weak, n_tied, n_dw, K, tau, violations, infeasible, label_err

Corpora
  * the SUPERSEDED CRC8 modes over the acquired real captures:
      captures_v21{,_val}.json  with CHK_LEN=3
      captures_v22{,_val}.json  with CHK_LEN=4
      captures_trim.json        with CHECK_EN=0 (legacy v2.0)
    -- these also prove no v2.3 threshold leaked backwards.
  * the NEW v2.3 synthetic corpus (fuzz_v23.cases), test AND production
    geometry, biased to the refusal classes v2.3 relaxes.
data/captures_val.json is never read.
"""
import argparse
import ctypes
import importlib.util
import subprocess
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(SC))
from harness import load_dataset, linearize                     # noqa: E402

CAUSES = {0: None, 1: "refuse_lock", 2: "refuse_marker",
          3: "refuse_infeasible", 4: "refuse_labelerr",
          5: "refuse_emitgate", 6: "refuse_nocand", 7: "refuse_admit",
          8: "refuse_chase"}
PATHS = {0: None, 1: "direct", 2: "chase", 3: "legacy_unverified"}


class DecInfo(ctypes.Structure):
    _fields_ = [("path", ctypes.c_uint8), ("cause", ctypes.c_uint8),
                ("trials", ctypes.c_uint8), ("alias_cmp", ctypes.c_uint8),
                ("chased", ctypes.c_uint8),
                ("n_weak", ctypes.c_uint16), ("n_tied", ctypes.c_uint16),
                ("K", ctypes.c_uint16), ("tau", ctypes.c_int16),
                ("violations", ctypes.c_uint8),
                ("infeasible", ctypes.c_uint16),
                ("label_err", ctypes.c_uint16), ("n_seg", ctypes.c_uint16),
                ("comps", ctypes.c_uint8), ("n_refs", ctypes.c_uint8),
                ("ref_split", ctypes.c_uint8)]


def _cfg(ev, *a, **kw):
    """_configure() + the chase-budget override, in that order (the
    reference resets A_MAX/T_MAX inside _configure)."""
    ev._configure(*a, **kw)
    # ONLY the v2.3 wire mode takes the override: decode.c's
    # `#define A_MAX A_MAX_CFG` sits inside `#if WIRE23`, so the v2.2/v2.1
    # compat geometries keep their historical 5/16 no matter what
    # -DA_MAX_CFG says -- and the reference must do the same or the
    # compat corpora would "mismatch" for the wrong reason.
    if CHASE[0] is not None and ev.WIRE == 23:
        ev.set_chase_budget(CHASE[0], CHASE[1])


def load_ref():
    spec = importlib.util.spec_from_file_location(
        "embedded_v2_p", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# BUILD-TIME chase budget (recon/AMAX_TMAX_SWEEP.md).  None = the
# decode.c / embedded_v2.py defaults, i.e. the shipped ledger 11 / 131, so
# the DEFAULT invocation -- the one `make verify` runs -- is unchanged.
CHASE = [None, None]


def build(nd, check_en, chk):
    tag = "%s_%s_%s" % (nd, 1 if check_en else 0, chk)
    if CHASE[0] is not None:
        tag += "_A%d_T%d" % (CHASE[0], CHASE[1])
    so = SC / ("parity_host_%s.so" % tag)
    cmd = ["gcc", "-O2", "-fPIC", "-shared", "-DND_DATA=%d" % nd,
           "-DCHECK_EN=%d" % (1 if check_en else 0), "-DUSE_ASM_SCAN=0",
           "-I", str(NEWIMPL), "-o", str(so), str(NEWIMPL / "decode.c")]
    if CHASE[0] is not None:
        cmd[4:4] = ["-DA_MAX_CFG=%d" % CHASE[0], "-DT_MAX_CFG=%d" % CHASE[1]]
    if check_en:
        cmd.insert(4, "-DCHK_LEN=%d" % chk)
    subprocess.run(cmd, check=True, capture_output=True)
    lib = ctypes.CDLL(str(so))
    lib.ws_decode_ex.restype = ctypes.c_uint8
    lib.ws_decode_ex.argtypes = [ctypes.c_char_p, ctypes.c_uint16,
                                 ctypes.c_char_p]
    return lib


FIELDS = (("trials", "trials"), ("alias_cmp", "alias_cmp"),
          ("comps", "comps"), ("n_refs", "n_refs"),
          ("ref_split", "ref_split"),
          ("n_weak", "n_weak"), ("n_tied", "n_tied"),
          ("K", "K"), ("tau", "tau"), ("violations", "violations"),
          ("infeasible", "infeasible"), ("label_err", "label_err"),
          ("n_dw", "n_dw"))


def compare(lib, ev, nd, raw, tag, fails):
    out = ctypes.create_string_buffer(nd)
    st = lib.ws_decode_ex(raw, len(raw), out)
    info = DecInfo.in_dll(lib, "dec_info")
    n_dw = ctypes.c_uint16.in_dll(lib, "v_ndw").value
    d_c = out.raw if st else None
    d_py, ipy = ev.decode_ex(linearize(raw.hex()))
    rows = []
    if d_c != d_py:
        rows.append(("bytes", d_c.hex() if d_c else None,
                     d_py.hex() if d_py else None))
    if PATHS[info.path] != ipy["path"]:
        rows.append(("path", PATHS[info.path], ipy["path"]))
    if CAUSES[info.cause] != ipy["cause"]:
        rows.append(("cause", CAUSES[info.cause], ipy["cause"]))
    if bool(info.chased) != bool(ipy.get("chased")):
        rows.append(("chased", info.chased, ipy.get("chased")))
    for cf, pf in FIELDS:
        if cf == "n_dw" and info.cause == 1:
            continue          # R1: no decision pass ran, counter stale
        cv = n_dw if cf == "n_dw" else getattr(info, cf)
        pv = ipy.get(pf, 0)
        if pv is None:
            pv = 0
        if cv != pv:
            rows.append((cf, cv, pv))
    if rows:
        fails.append((tag, rows))
    return not rows


def run_corpus(lib, ev, nd, caps, name):
    fails = []
    n_ok = 0
    for c in caps:
        raw = bytes.fromhex(c["capture"])
        tag = "%s r%s" % (c.get("pattern"), c.get("rep"))
        if c.get("trim") is not None:
            tag = "trim%s %s" % (c["trim"], tag)
        n_ok += compare(lib, ev, nd, raw, tag, fails)
    print("%-30s %4d/%4d bit-identical" % (name, n_ok, len(caps)))
    for t, r in fails[:8]:
        print("    MISMATCH", t, r[:5])
    return n_ok == len(caps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-fuzz", action="store_true")
    ap.add_argument("--amax", type=int, default=None,
                    help="chase A_MAX (default: decode.c's own 11)")
    ap.add_argument("--tmax", type=int, default=None,
                    help="chase T_MAX (default: decode.c's own 131)")
    a = ap.parse_args()
    if (a.amax is None) != (a.tmax is None):
        raise SystemExit("--amax and --tmax must be given together")
    if a.amax is not None:
        CHASE[0], CHASE[1] = a.amax, a.tmax
        print("chase budget: A_MAX=%d T_MAX=%d (both sides)"
              % (a.amax, a.tmax))
    ev = load_ref()
    data = NEWIMPL / "data"
    ok = True
    # ---- superseded CRC8 modes over the acquired real captures --------
    for chk, files in ((3, ("captures_v21.json", "captures_v21_val.json")),
                       (4, ("captures_v22.json", "captures_v22_val.json"))):
        lib = build(16, True, chk)
        for f in files:
            _cfg(ev, 16, chk=chk)
            _, caps = load_dataset(str(data / f))
            ok &= run_corpus(lib, ev, 16, caps, "%s (CHK_LEN=%d)" % (f, chk))
    lib = build(16, False, 0)
    _cfg(ev, 16, check=False)
    _, caps = load_dataset(str(data / "captures_trim.json"))
    ok &= run_corpus(lib, ev, 16, caps, "captures_trim.json (legacy v2.0)")
    # ---- the new v2.3 corpus ------------------------------------------
    if not a.skip_fuzz:
        import fuzz_v23
        for nd in (16, 48):
            lib = build(nd, True, 6)
            _cfg(ev, nd, chk=6)
            cases = fuzz_v23.cases(nd)
            fails = []
            n_ok = 0
            for (tag, raw, _truth, _cls) in cases:
                n_ok += compare(lib, ev, nd, raw, tag, fails)
            print("%-30s %4d/%4d bit-identical"
                  % ("fuzz_v23 ND=%d (v2.3)" % nd, n_ok, len(cases)))
            for t, r in fails[:8]:
                print("    MISMATCH", t, r[:5])
            ok &= (n_ok == len(cases))
    print("HOST PARITY (decode.c vs embedded_v2.py)%s:"
          % ("" if CHASE[0] is None
             else " at A_MAX=%d T_MAX=%d" % (CHASE[0], CHASE[1])),
          "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
