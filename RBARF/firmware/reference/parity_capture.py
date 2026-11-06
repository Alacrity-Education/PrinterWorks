#!/usr/bin/env python3
"""Byte-exactness proof for reference/rbarf_capture.c (layer 2, the sampler).

Modelled on reference/parity_readable.py: compile the C on the host with
gcc, drive it through ctypes, and diff its output BYTE FOR BYTE against the
normative Python sampler recon/approaches/dev_prod/v23lib.capture() -- which
is recon/synth.py's model, the one fitted to the 54 real captures.

What is compared: every byte of every capture.  Not a summary statistic, not
a decode outcome -- the raw bytes the sampling loop would have written.  A
single differing byte anywhere fails the run.

Corpora
  a) the production grid: the 70 distinct ND=48 payloads of
     bench/suite_singleshot.build_suite() x 6 eps points x 48 arm phases
     = 20 160 captures of 288 bytes.  Same grid points parity_readable.py
     uses, so the two proofs stack: this one says the C sampler produces
     the same bytes, that one says the C decoder turns them into the same
     answer.
  b) the malformations v23lib exposes -- drift (linear eps ramp), trunc
     (buffer ran out, TAIL missing) and chop (arm fired late, HEAD
     missing), alone and in combination.
  c) the ND=16 test geometry (30 payloads from bench/patterns.py), because
     the real-silicon corpus is that geometry and the capture length
     differs (160 bytes, not 288).
  d) a t0 sweep straight through the 681 ns trigger-phase cliff and out to
     1300 ns, where the arm must never land but the model still has to be
     right.

Also runs rbarf_capture.c's own self-checks (the rendered assembly's RLC
bit-packing against the model's packer, the four hand-assembled BTJT
offsets, and the two wire representations against each other).

data/captures_val.json is never opened; no bench script is modified.

  python3 reference/parity_capture.py            # everything
  python3 reference/parity_capture.py --skip-grid
  python3 reference/parity_capture.py --jobs 1   # single process
"""
import argparse
import ctypes
import multiprocessing
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEWIMPL = HERE.parent
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
sys.path.insert(0, str(NEWIMPL / "bench"))

SO = HERE / "librbarf_capture.so"

CAP_BYTES_PROD = 288          # rbarf_prod.c CAP_BYTES
CAP_BYTES_TEST = 160          # v23lib.CAP_BYTES_TEST

# The same six eps points and 48 arm phases parity_readable.py sweeps: the
# arm phases span the production arm's measured t0 range, 70..658 ns.
GRID_EPS = (-0.014, -0.0105, -0.009, -0.008, -0.006, -0.004)
GRID_ARM = tuple(70.0 + i * (658.0 - 70.0) / 47.0 for i in range(48))

# Corpus (b): every malformation v23lib.capture() accepts, as kwargs.
#   drift  linear eps ramp across the wire span, centred on eps
#   trunc  drop the last N capture bytes
#   chop   drop the first N and shift left (zero-filled tail)
VARIANTS = (
    ("drift +0.2%",        dict(drift=+0.002)),
    ("drift -0.2%",        dict(drift=-0.002)),
    ("drift +0.6%",        dict(drift=+0.006)),
    ("drift -0.6%",        dict(drift=-0.006)),
    ("trunc 1",            dict(trunc=1)),
    ("trunc 16",           dict(trunc=16)),
    ("trunc 64",           dict(trunc=64)),
    ("chop 1",             dict(chop=1)),
    ("chop 8",             dict(chop=8)),
    ("chop 40",            dict(chop=40)),
    ("chop 3 + trunc 7",   dict(chop=3, trunc=7)),
    ("drift +0.4% chop 2 trunc 5",
     dict(drift=+0.004, chop=2, trunc=5)),
)
VARIANT_EPS = (-0.014, -0.0105, -0.004)
VARIANT_ARM = (70.0, 385.0, 658.0)

# Corpus (d): straight through the cliff.  t0_crit at eps = -1.05 % is
# 1250 - 562.5/(1+eps) = 681.4 ns; the arm must stay below it, but the
# model has to be right on both sides of it.
CLIFF_ARM = tuple(float(t) for t in range(0, 1301, 25))
CLIFF_EPS = (-0.0105, 0.0)


# ---------------------------------------------------------------- build
def build():
    """gcc the readable capture model into a shared library, refusing to
    continue on any warning at the flags README.md advertises."""
    warn = subprocess.run(
        ["gcc", "-std=c99", "-Wall", "-Wextra", "-pedantic", "-O2",
         "-c", str(HERE / "rbarf_capture.c"), "-o", "/dev/null"],
        capture_output=True, text=True)
    if warn.returncode != 0:
        sys.stderr.write(warn.stderr)
        raise SystemExit("rbarf_capture.c does not compile")
    if warn.stderr.strip():
        sys.stderr.write(warn.stderr)
        raise SystemExit("rbarf_capture.c compiled with warnings")
    subprocess.run(["gcc", "-std=c99", "-O2", "-fPIC", "-shared",
                    "-o", str(SO), str(HERE / "rbarf_capture.c"), "-lm"],
                   check=True)


def load_lib():
    lib = ctypes.CDLL(str(SO))
    lib.rbarf_capture_v23.restype = ctypes.c_uint16
    lib.rbarf_capture_v23.argtypes = [
        ctypes.c_char_p, ctypes.c_uint8,                  # data, nd
        ctypes.c_double, ctypes.c_double, ctypes.c_double,  # eps, t0, drift
        ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16,  # nbytes,chop,trunc
        ctypes.c_char_p, ctypes.c_uint16]                  # out, out_cap
    lib.rbarf_capture_selfcheck.restype = ctypes.c_int
    lib.rbarf_capture_selfcheck.argtypes = [ctypes.c_int]
    return lib


def c_capture(lib, buf, data, eps, t0, ncap, drift=0.0, trunc=0, chop=0):
    """The C model, called with v23lib.capture()'s own argument order."""
    n = lib.rbarf_capture_v23(data, len(data), eps, t0, drift,
                              ncap, chop, trunc, buf, len(buf))
    return buf.raw[:n]


# ---------------------------------------------------------------- tally
class Tally:
    """agree/total per capture AND per byte, plus the first few offenders."""

    def __init__(self, name):
        self.name = name
        self.total = 0
        self.agree = 0
        self.bytes_total = 0
        self.bytes_agree = 0
        self.fails = []

    def add(self, tag, c, p):
        self.total += 1
        n = max(len(c), len(p))
        self.bytes_total += n
        if c == p:
            self.agree += 1
            self.bytes_agree += n
        else:
            same = sum(1 for a, b in zip(c, p) if a == b)
            self.bytes_agree += same
            if len(self.fails) < 8:
                first = next((i for i, (a, b) in enumerate(zip(c, p))
                              if a != b), None)
                self.fails.append((tag, len(c), len(p), first,
                                   n - same))

    def merge(self, other):
        self.total += other.total
        self.agree += other.agree
        self.bytes_total += other.bytes_total
        self.bytes_agree += other.bytes_agree
        self.fails.extend(other.fails[:max(0, 8 - len(self.fails))])

    @property
    def perfect(self):
        return self.total > 0 and self.agree == self.total

    def report(self):
        print("%-46s %6d/%-6d %13d/%-13d %s"
              % (self.name, self.agree, self.total,
                 self.bytes_agree, self.bytes_total,
                 "BYTE-IDENTICAL" if self.perfect else "MISMATCH"))
        for tag, lc, lp, first, nbad in self.fails:
            print("      case %s: len C %d / py %d, first diff at %s, "
                  "%d bytes differ" % (tag, lc, lp, first, nbad))


# ---------------------------------------------------------------- payloads
def prod_payloads():
    """The 70 production-geometry payloads of bench/suite_singleshot.py,
    imported by path the way parity_readable.py imports them (the bench
    script itself is never touched)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "suite_singleshot_cap", NEWIMPL / "bench" / "suite_singleshot.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return [(name, data) for (_fam, name, data) in m.build_suite()]


def test_payloads():
    """The 30 ND=16 test payloads (bench/patterns.py PATTERNS +
    VAL_PATTERNS, both plain byte tables -- no capture corpus is read)."""
    import v23lib
    return sorted(v23lib.test_payloads().items())


# ------------------------------------------------------- worker plumbing
_W = {}


def _init():
    import v23lib
    _W["L"] = v23lib
    _W["lib"] = load_lib()
    _W["buf"] = ctypes.create_string_buffer(1024)
    _W["prod"] = prod_payloads()
    _W["test"] = test_payloads()


def _chunk(job):
    """job = (corpus, [(payload_index, eps, t0, kwargs), ...])"""
    corpus, items = job
    L, lib, buf = _W["L"], _W["lib"], _W["buf"]
    pay = _W["prod"] if corpus != "test" else _W["test"]
    ncap = CAP_BYTES_PROD if corpus != "test" else CAP_BYTES_TEST
    t = Tally("chunk")
    for (ip, eps, t0, kw) in items:
        name, data = pay[ip]
        p = L.capture(data, eps, t0, ncap=ncap, **kw)
        c = c_capture(lib, buf, data, eps, t0, ncap, **kw)
        tag = "%s eps%+.4f t0=%.1f%s" % (
            name, eps, t0, (" " + repr(kw)) if kw else "")
        t.add(tag, c, p)
    return t


def run(name, jobs, corpus, items, chunk=48):
    chunks = [(corpus, items[i:i + chunk])
              for i in range(0, len(items), chunk)]
    total = Tally(name)
    if jobs == 1:
        _init()
        for c in chunks:
            total.merge(_chunk(c))
    else:
        with multiprocessing.Pool(jobs, initializer=_init) as pool:
            for t in pool.imap_unordered(_chunk, chunks):
                total.merge(t)
    return total


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-grid", action="store_true")
    ap.add_argument("--skip-variants", action="store_true")
    ap.add_argument("--jobs", type=int,
                    default=min(24, multiprocessing.cpu_count()))
    a = ap.parse_args()

    build()
    lib = load_lib()

    print("reference/rbarf_capture.c (layer 2, the sampler) vs "
          "recon/approaches/dev_prod/v23lib.capture()")
    print("the fitted model: LOOP 40 cy, gaps [4,5,4,4,4,6,5,8], "
          "w[] [0,-1,0,+2,0,0,0,+1], T1H 752 / T0H 377 ns")
    print()

    # ---- layer 1 / internal self-checks ------------------------------
    fails = lib.rbarf_capture_selfcheck(0)
    print("rbarf_capture.c self-checks (rendered RLC chain == model "
          "packer, the 4 BTJT poll offsets, bit-seq == edge-list, the arm's "
          "control flow and cycle sums): %s"
          % ("PASS" if fails == 0 else "FAIL, %d check(s)" % fails))
    print()

    print("%-46s %13s %27s %s"
          % ("corpus", "captures", "bytes", "verdict"))
    tallies = []

    n_prod = len(prod_payloads())
    n_test = len(test_payloads())

    # ---- (a) the production grid -------------------------------------
    if not a.skip_grid:
        items = [(ip, eps, t0, {})
                 for ip in range(n_prod)
                 for eps in GRID_EPS
                 for t0 in GRID_ARM]
        tallies.append(run(
            "prod grid ND=48 (%d pay x %d eps x %d t0)"
            % (n_prod, len(GRID_EPS), len(GRID_ARM)),
            a.jobs, "prod", items))
        tallies[-1].report()

    # ---- (b) the malformations ---------------------------------------
    if not a.skip_variants:
        for vname, kw in VARIANTS:
            items = [(ip, eps, t0, kw)
                     for ip in range(n_prod)
                     for eps in VARIANT_EPS
                     for t0 in VARIANT_ARM]
            tallies.append(run("v23lib variant: %s" % vname,
                               a.jobs, "prod", items))
            tallies[-1].report()

    # ---- (c) the ND=16 test geometry ---------------------------------
    items = [(ip, eps, t0, {})
             for ip in range(n_test)
             for eps in GRID_EPS
             for t0 in GRID_ARM[::4]]
    tallies.append(run("test geometry ND=16, 160 B captures",
                       a.jobs, "test", items))
    tallies[-1].report()

    # ---- (d) through the trigger-phase cliff -------------------------
    items = [(ip, eps, t0, {})
             for ip in range(0, n_prod, 7)
             for eps in CLIFF_EPS
             for t0 in CLIFF_ARM]
    tallies.append(run("t0 sweep 0..1300 ns (through the 681 ns cliff)",
                       a.jobs, "prod", items))
    tallies[-1].report()

    n_cases = sum(t.total for t in tallies)
    n_bytes = sum(t.bytes_total for t in tallies)
    n_agree = sum(t.agree for t in tallies)
    n_bagree = sum(t.bytes_agree for t in tallies)
    ok = all(t.perfect for t in tallies) and fails == 0

    print()
    print("  captures %d/%d   bytes %d/%d" % (n_agree, n_cases,
                                              n_bagree, n_bytes))
    print()
    print("CAPTURE PARITY: %s -- %d captures, %d capture bytes, "
          "100%% agreement %s"
          % ("PASS" if ok else "FAIL", n_cases, n_bytes,
             "confirmed" if ok else "NOT reached"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
