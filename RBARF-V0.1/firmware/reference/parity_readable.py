#!/usr/bin/env python3
"""Bit-exactness proof for reference/rbarf_decoder.c.

Modelled on recon/approaches/dev_prod/parity_v23.py: compile the C on the
host with gcc, run it over every corpus through ctypes, and diff it field by
field against the NORMATIVE Python decoder recon/approaches/embedded_v2.py
at its default parameters (v2.3 wire, A_MAX = 11, T_MAX = 131, Lever B on).

Diffed contract, per capture:
    emitted bytes | refusal   (byte-identical)
    path          (direct / chase / None)
    refusal cause (the R1..R8 label)
    chased, trials, comps, n_refs, ref_split,
    n_weak, n_tied, n_dw, K, tau, violations, infeasible, label_err

Corpora
  a) data/captures_v23.json          54 REAL-SILICON captures, ND = 16
  b) dev_prod/fuzz_v23.cases(nd)     the same adversarial fuzz sets
                                     parity_v23.py uses, ND = 16 and 48
  c) a synthetic v23lib grid at ND = 48: 6 eps points x 48 arm phases x the
     70 payloads of bench/suite_singleshot.build_suite() = 20 160 captures
  d) degenerate buffers (empty / constant / random / truncated real
     captures), which is where the R1 lock refusal and the s16 wrap paths
     live -- nothing else in a) to c) reaches them

data/captures_val.json is never read.

  python3 reference/parity_readable.py            # everything
  python3 reference/parity_readable.py --skip-grid
  python3 reference/parity_readable.py --jobs 1   # single process
  python3 reference/parity_readable.py --source /tmp/work/rbarf_decoder.c

--source points the harness at another copy of the decoder (a working copy
under development, say).  It must sit beside a rbarf_decoder.h it can
#include; the shared library is built next to it.  A copy of THIS script
run from outside reference/ additionally needs RBARF_TREE=<src>
in the environment so it can still find the corpora.
"""
import argparse
import collections
import ctypes
import importlib.util
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The tree the corpora and the normative Python decoder are read from.
# Normally the directory above this file.  RBARF_TREE overrides it, which
# is what lets a WORKING COPY of this script (living outside reference/)
# test a working copy of the decoder via --source.
NEWIMPL = Path(os.environ.get("RBARF_TREE") or HERE.parent).resolve()
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
sys.path.insert(0, str(NEWIMPL / "bench"))

from harness import load_dataset, linearize                     # noqa: E402

# The decoder under test, and the shared library built from it.  Both are
# overridden by --source; they are passed explicitly to the grid workers
# because a forkserver pool does not inherit main()'s globals.
SRC = HERE / "rbarf_decoder.c"
SO = HERE / "librbarf_readable.so"


def so_for(src):
    """Where to build the shared library for a given source path."""
    src = Path(src).resolve()
    if src == (HERE / "rbarf_decoder.c"):
        return HERE / "librbarf_readable.so"
    return src.with_name("lib" + src.stem + "_readable.so")

# ---- the two enums of rbarf_decoder.h, as the reference spells them -------
CAUSES = {0: None, 1: "refuse_lock", 2: "refuse_marker",
          3: "refuse_infeasible", 4: "refuse_labelerr",
          6: "refuse_nocand", 7: "refuse_admit", 8: "refuse_chase"}
# the reference has ONE "chase" label; the C file distinguishes the weight
PATHS = {0: None, 1: "direct", 2: "chase", 3: "chase"}

# (C field, embedded_v2 info key)
FIELDS = (("trials", "trials"), ("comps", "comps"), ("n_refs", "n_refs"),
          ("ref_split", "ref_split"), ("n_weak", "n_weak"),
          ("n_tied", "n_tied"), ("n_dw", "n_dw"),
          ("bit_period_q", "K"), ("phase_offset", "tau"),
          ("marker_violations", "violations"),
          ("infeasible", "infeasible"), ("label_error", "label_err"))
ALL_FIELDS = ("bytes", "path", "cause", "chased") + tuple(c for c, _ in FIELDS)

# the synthetic grid (corpus c)
GRID_EPS = (-0.014, -0.0105, -0.009, -0.008, -0.006, -0.004)
GRID_ARM = tuple(70.0 + i * (658.0 - 70.0) / 47.0 for i in range(48))


class Result(ctypes.Structure):
    """Mirror of rbarf_result.  Any layout drift would show up instantly as
    a mass mismatch, and the size assert below catches the obvious cases."""
    _fields_ = [("data", ctypes.c_uint8 * 48),
                ("data_len", ctypes.c_uint8),
                ("cause", ctypes.c_uint8),
                ("path", ctypes.c_uint8),
                ("trials", ctypes.c_uint8),
                ("comps", ctypes.c_uint8),
                ("n_refs", ctypes.c_uint8),
                ("ref_split", ctypes.c_uint8),
                ("chased", ctypes.c_uint8),
                ("marker_violations", ctypes.c_uint8),
                ("reserved", ctypes.c_uint8),
                ("n_weak", ctypes.c_uint16),
                ("n_tied", ctypes.c_uint16),
                ("n_dw", ctypes.c_uint16),
                ("n_segments", ctypes.c_uint16),
                ("infeasible", ctypes.c_uint16),
                ("label_error", ctypes.c_uint16),
                ("bit_period_q", ctypes.c_uint16),
                ("phase_offset", ctypes.c_int16)]


assert ctypes.sizeof(Result) == 74, ctypes.sizeof(Result)


def build():
    """gcc the readable decoder into a shared library (and check that it
    still compiles warning-free at the flags README.md advertises)."""
    warn = subprocess.run(
        ["gcc", "-std=c99", "-Wall", "-Wextra", "-pedantic", "-O2",
         "-c", str(SRC), "-o", "/dev/null"],
        capture_output=True, text=True)
    if warn.returncode != 0:
        sys.stderr.write(warn.stderr)
        raise SystemExit("%s does not compile" % SRC)
    if warn.stderr.strip():
        sys.stderr.write(warn.stderr)
        raise SystemExit("%s compiled with warnings" % SRC)
    subprocess.run(["gcc", "-std=c99", "-O2", "-fPIC", "-shared",
                    "-o", str(SO), str(SRC)], check=True)


def load_lib(nd):
    lib = ctypes.CDLL(str(SO))
    lib.rbarf_decoder_configure.restype = ctypes.c_bool
    lib.rbarf_decoder_configure.argtypes = [ctypes.c_uint8]
    lib.rbarf_decode.restype = ctypes.c_bool
    lib.rbarf_decode.argtypes = [ctypes.c_char_p, ctypes.c_uint16,
                                 ctypes.POINTER(Result)]
    if not lib.rbarf_decoder_configure(nd):
        raise SystemExit("rbarf_decoder_configure(%d) refused" % nd)
    return lib


def load_ref(nd):
    """A fresh embedded_v2 instance at DEFAULT parameters, ND = nd."""
    spec = importlib.util.spec_from_file_location(
        "embedded_v2_readable",
        NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._configure(nd, chk=6)
    return m


def compare(lib, ev, nd, raw):
    """One capture through both decoders.  Returns (set of agreeing field
    names, list of (field, c_value, py_value) disagreements)."""
    res = Result()
    ok = lib.rbarf_decode(raw, len(raw), ctypes.byref(res))
    data_c = bytes(res.data[:res.data_len]) if ok else None
    data_py, info = ev.decode_ex(linearize(raw.hex()))

    agree, bad = set(), []

    def check(name, cv, pv):
        if cv == pv:
            agree.add(name)
        else:
            bad.append((name, cv, pv))

    outcome = PATHS[res.path] or CAUSES[res.cause] or "?"
    check("bytes", data_c, data_py)
    check("path", PATHS[res.path], info["path"])
    check("cause", CAUSES[res.cause], info["cause"])
    check("chased", bool(res.chased), bool(info.get("chased")))
    for cf, pf in FIELDS:
        if cf == "n_dw" and res.cause == 1:
            # R1: no decision pass ran, so the reference never publishes the
            # counter (parity_v23.py skips it here for the same reason).
            agree.add(cf)
            continue
        pv = info.get(pf, 0)
        check(cf, getattr(res, cf), 0 if pv is None else pv)
    return agree, bad, outcome


class Tally:
    """agree/total per field, plus the first few offending cases."""

    def __init__(self, name):
        self.name = name
        self.total = 0
        self.agree = dict((f, 0) for f in ALL_FIELDS)
        self.outcomes = collections.Counter()
        self.fails = []

    def add(self, tag, agree, bad, outcome):
        self.total += 1
        self.outcomes[outcome] += 1
        for f in agree:
            self.agree[f] += 1
        if bad and len(self.fails) < 8:
            self.fails.append((tag, bad[:4]))

    def merge(self, other):
        self.total += other.total
        for f in ALL_FIELDS:
            self.agree[f] += other.agree[f]
        self.outcomes.update(other.outcomes)
        self.fails.extend(other.fails[:max(0, 8 - len(self.fails))])

    @property
    def perfect(self):
        return all(self.agree[f] == self.total for f in ALL_FIELDS)

    def report(self):
        worst = min(self.agree[f] for f in ALL_FIELDS) if self.total else 0
        print("%-42s %6d/%-6d %s" % (self.name, worst, self.total,
                                     "ALL FIELDS IDENTICAL" if self.perfect
                                     else "MISMATCH"))
        print("      outcomes: %s" % ", ".join(
            "%s %d" % (k, v) for k, v in sorted(self.outcomes.items())))
        if not self.perfect:
            for f in ALL_FIELDS:
                if self.agree[f] != self.total:
                    print("      %-18s %6d/%d" % (f, self.agree[f], self.total))
            for tag, bad in self.fails:
                print("      case %s: %s" % (tag, bad))


def degenerate_cases(caps):
    """Buffers that are not frames at all: the R1/R2 corner.  Deterministic."""
    out = []
    for fill in (0x00, 0xFF, 0xAA, 0x55, 0x0F):
        for n in (0, 1, 2, 7, 64, 288, 640):
            out.append(("fill%02X x%d" % (fill, n), bytes([fill]) * n))
    x = 0x1234
    for n in (16, 64, 288, 640):
        buf = bytearray()
        while len(buf) < n:
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
            buf.append((x >> 16) & 0xFF)
        out.append(("lcg x%d" % n, bytes(buf)))
    real = bytes.fromhex(caps[0]["capture"])
    for n in (8, 16, 32, 64, 128, 300, 500, len(real) - 1):
        out.append(("real[:%d]" % n, real[:n]))
    for skip in (1, 3, 8, 40):
        out.append(("real[%d:]" % skip, real[skip:]))
    return out


def run_serial(name, nd, cases):
    """cases: iterable of (tag, raw_capture_bytes)."""
    lib, ev = load_lib(nd), load_ref(nd)
    t = Tally(name)
    for tag, raw in cases:
        agree, bad, outcome = compare(lib, ev, nd, raw)
        t.add(tag, agree, bad, outcome)
    return t


# ---------------------------------------------------------------- corpus (c)
_W = {}


def _grid_init(src=None, so=None):
    import v23lib
    global SRC, SO
    if src is not None:
        SRC, SO = Path(src), Path(so)
    _W["L"] = v23lib
    _W["lib"] = load_lib(48)
    _W["ev"] = load_ref(48)
    _W["pay"] = grid_payloads()


def _grid_chunk(chunk):
    L, lib, ev, pay = _W["L"], _W["lib"], _W["ev"], _W["pay"]
    t = Tally("chunk")
    for (ip, ie, ia) in chunk:
        name, data = pay[ip]
        eps, t0 = GRID_EPS[ie], GRID_ARM[ia]
        raw = L.capture(data, eps, t0)
        agree, bad, outcome = compare(lib, ev, 48, raw)
        t.add("%s eps%+.4f t0=%.1f" % (name, eps, t0), agree, bad, outcome)
    return t


def grid_payloads():
    """The 70 production-geometry payloads of bench/suite_singleshot.py,
    imported the way that script's own tables are imported elsewhere in the
    tree (load the module by path; the bench script itself is untouched)."""
    spec = importlib.util.spec_from_file_location(
        "suite_singleshot_ref", NEWIMPL / "bench" / "suite_singleshot.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return [(name, data) for (_fam, name, data) in m.build_suite()]


def run_grid(jobs):
    n_pay = len(grid_payloads())
    jobs_list = [(ip, ie, ia)
                 for ip in range(n_pay)
                 for ie in range(len(GRID_EPS))
                 for ia in range(len(GRID_ARM))]
    name = ("v23lib synth grid ND=48 (%d eps x %d arm x %d pay)"
            % (len(GRID_EPS), len(GRID_ARM), n_pay))
    chunks = [jobs_list[i:i + 64] for i in range(0, len(jobs_list), 64)]
    total = Tally(name)
    if jobs == 1:
        _grid_init()
        for c in chunks:
            total.merge(_grid_chunk(c))
    else:
        with multiprocessing.Pool(jobs, initializer=_grid_init,
                                  initargs=(str(SRC), str(SO))) as pool:
            for t in pool.imap_unordered(_grid_chunk, chunks):
                total.merge(t)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-fuzz", action="store_true")
    ap.add_argument("--skip-grid", action="store_true")
    ap.add_argument("--jobs", type=int,
                    default=min(24, multiprocessing.cpu_count()))
    ap.add_argument("--source", metavar="PATH", default=None,
                    help="decoder .c to test (default: the one beside this "
                         "script)")
    a = ap.parse_args()

    global SRC, SO
    if a.source:
        SRC = Path(a.source).resolve()
        SO = so_for(SRC)

    build()
    shown = (SRC.relative_to(NEWIMPL) if SRC.is_relative_to(NEWIMPL) else SRC)
    print("%s vs recon/approaches/embedded_v2.py "
          "(defaults: v2.3, A_MAX=11, T_MAX=131, DW_EN=1)" % shown)
    print("%-42s %13s %s" % ("corpus", "agree/total", "verdict"))
    tallies = []

    # ---- (a) real silicon --------------------------------------------
    _meta, caps = load_dataset(str(NEWIMPL / "data" / "captures_v23.json"))
    tallies.append(run_serial(
        "data/captures_v23.json (real silicon)", 16,
        [("%s r%s" % (c.get("pattern"), c.get("rep")),
          bytes.fromhex(c["capture"])) for c in caps]))
    tallies[-1].report()

    # ---- (b) the fuzz corpora ----------------------------------------
    if not a.skip_fuzz:
        import fuzz_v23
        for nd in (16, 48):
            cases = [(tag, raw) for (tag, raw, _t, _c) in fuzz_v23.cases(nd)]
            tallies.append(run_serial("fuzz_v23 ND=%d (adversarial)" % nd,
                                      nd, cases))
            tallies[-1].report()

    # ---- (c) the synthetic grid --------------------------------------
    if not a.skip_grid:
        tallies.append(run_grid(a.jobs))
        tallies[-1].report()

    # ---- (d) degenerate buffers --------------------------------------
    tallies.append(run_serial("degenerate buffers (R1/R2 corner)", 16,
                              degenerate_cases(caps)))
    tallies[-1].report()

    n_cases = sum(t.total for t in tallies)
    ok = all(t.perfect for t in tallies)
    print("")
    for f in ALL_FIELDS:
        n = sum(t.agree[f] for t in tallies)
        print("  field %-18s %7d/%-7d %s"
              % (f, n, n_cases, "OK" if n == n_cases else "MISMATCH"))
    print("")
    print("READABLE PARITY: %s -- %d captures, %d compared fields, "
          "100%% agreement %s"
          % ("PASS" if ok else "FAIL", n_cases, len(ALL_FIELDS),
             "confirmed" if ok else "NOT reached"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
