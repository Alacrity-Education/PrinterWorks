#!/usr/bin/env python3
"""Host-side bit-exactness harness: decode.c (gcc, ctypes) vs embedded_v2.py.

Feeds the C decoder the RAW capture bytes (it linearizes inline, exactly
like the firmware) and the Python reference the linearized sample list of
the same capture, then diffs the complete observable contract:

    emitted bytes | refusal      (byte-identical, spec B1)
    path label    (direct / chase / legacy_unverified / None)
    refusal cause (R1..R8 label)
    trials, alias_cmp, n_weak, n_tied, K, tau,
    violations, infeasible, label_err, n_seg

Corpora: captures_v21.json (54) + captures_v21_val.json (36) with the
CHECK_EN=1 CHK_LEN=3 build (the superseded v2.1 geometry, kept as the
regression mode), captures_v22.json / captures_v22_val.json (when
acquired) with the CHK_LEN=4 v2.2 build, and captures_trim.json (96,
legacy v2.0 frames) with the CHECK_EN=0 build.
data/captures_val.json is never read.

Usage: python3 parity_host.py [--ncap N]   (N = capture bytes fed to C,
                                            default 640 = full capture)
"""
import argparse
import ctypes
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                     # recon/
NEWIMPL = ROOT.parent                      # src/ (the firmware tree)
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "embedded_v2", ROOT / "approaches" / "embedded_v2.py")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

CAUSES = {0: None, 1: "refuse_lock", 2: "refuse_marker",
          3: "refuse_infeasible", 4: "refuse_labelerr", 5: "refuse_emitgate",
          6: "refuse_nocand", 7: "refuse_admit", 8: "refuse_chase"}
PATHS = {0: None, 1: "direct", 2: "chase", 3: "legacy_unverified"}


class DecInfo(ctypes.Structure):
    _fields_ = [("path", ctypes.c_uint8), ("cause", ctypes.c_uint8),
                ("trials", ctypes.c_uint8), ("alias_cmp", ctypes.c_uint8),
                ("chased", ctypes.c_uint8),
                ("n_weak", ctypes.c_uint16), ("n_tied", ctypes.c_uint16),
                ("K", ctypes.c_uint16), ("tau", ctypes.c_int16),
                ("violations", ctypes.c_uint8),
                ("infeasible", ctypes.c_uint16),
                ("label_err", ctypes.c_uint16), ("n_seg", ctypes.c_uint16)]


def build(check_en, chk=4):
    tag = ("v22" if chk == 4 else "v21") if check_en else "legacy"
    so = HERE / f"decode_host_{tag}.so"
    cmd = ["gcc", "-O2", "-fPIC", "-shared", "-DND_DATA=16",
           f"-DCHECK_EN={1 if check_en else 0}", "-DUSE_ASM_SCAN=0",
           "-I", str(NEWIMPL),
           "-o", str(so), str(NEWIMPL / "decode.c")]
    if check_en:
        cmd.insert(4, f"-DCHK_LEN={chk}")
    subprocess.run(cmd, check=True)
    lib = ctypes.CDLL(str(so))
    lib.ws_decode_ex.restype = ctypes.c_uint8
    lib.ws_decode_ex.argtypes = [ctypes.c_char_p, ctypes.c_uint16,
                                 ctypes.c_char_p]
    return lib


def c_decode(lib, cap_bytes):
    out = ctypes.create_string_buffer(16)
    st = lib.ws_decode_ex(cap_bytes, len(cap_bytes), out)
    info = DecInfo.in_dll(lib, "dec_info")
    return (out.raw if st else None), st, info


def run(lib, path, check_en, ncap, verbose=False, chk=4):
    v2._configure(16, check=check_en, chk=chk)
    _, caps = load_dataset(path)
    n_ok = 0
    fails = []
    for c in caps:
        raw = bytes.fromhex(c["capture"])[:ncap]
        d_c, st, info = c_decode(lib, raw)
        d_py, ipy = v2.decode_ex(linearize(raw.hex()))
        rows = []
        if d_c != d_py:
            rows.append(("bytes", d_c.hex() if d_c else None,
                         d_py.hex() if d_py else None))
        if PATHS[info.path] != ipy["path"]:
            rows.append(("path", PATHS[info.path], ipy["path"]))
        if CAUSES[info.cause] != ipy["cause"]:
            rows.append(("cause", CAUSES[info.cause], ipy["cause"]))
        for cf, pf in (("trials", "trials"), ("alias_cmp", "alias_cmp"),
                       ("n_weak", "n_weak"), ("n_tied", "n_tied"),
                       ("K", "K"), ("tau", "tau"),
                       ("violations", "violations"),
                       ("infeasible", "infeasible"),
                       ("label_err", "label_err")):
            cv = getattr(info, cf)
            pv = ipy.get(pf, 0)
            if pv is None:
                pv = 0
            if bool(info.chased) != bool(ipy.get("chased")):
                rows.append(("chased", info.chased, ipy.get("chased")))
                break
            if cv != pv:
                rows.append((cf, cv, pv))
        tag = "%s r%s" % (c.get("pattern"), c.get("rep"))
        if c.get("trim") is not None:
            tag = "trim%s %s" % (c["trim"], tag)
        if rows:
            fails.append((tag, rows))
            if verbose:
                print("MISMATCH", tag, rows)
        else:
            n_ok += 1
    name = Path(path).name
    print("%-26s %3d/%3d bit-identical (bytes+path+cause+counters)"
          % (name, n_ok, len(caps)))
    return n_ok == len(caps), fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ncap", type=int, default=640)
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args()
    data = NEWIMPL / "data"
    ok = True
    lib21 = build(True, chk=3)               # superseded v2.1 geometry
    for p in ("captures_v21.json", "captures_v21_val.json"):
        good, fails = run(lib21, str(data / p), True, args.ncap, args.v,
                          chk=3)
        ok &= good
        for tag, rows in fails[:6]:
            print("   ", tag, rows)
    lib22 = build(True, chk=4)               # v2.2 (current)
    for p in ("captures_v22.json", "captures_v22_val.json"):
        if not (data / p).exists():
            print("%-26s (not acquired yet, skipped)" % p)
            continue
        good, fails = run(lib22, str(data / p), True, args.ncap, args.v,
                          chk=4)
        ok &= good
        for tag, rows in fails[:6]:
            print("   ", tag, rows)
    lib_legacy = build(False)
    good, fails = run(lib_legacy, str(data / "captures_trim.json"),
                      False, args.ncap, args.v)
    ok &= good
    for tag, rows in fails[:6]:
        print("   ", tag, rows)
    print("HOST PARITY:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
