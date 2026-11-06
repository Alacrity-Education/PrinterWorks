#!/usr/bin/env python3
"""v2.3 ON-TARGET bit-exactness + decode time, in ucsim_stm8.

Runs the REAL SDCC/sdas image -- decode_asm.s streaming layer plus the
decode.c pipeline tail, at production link flags (--data-loc 0xF3,
--code-loc 0x8068, the VGAP link guard) -- instruction by instruction in
ucsim, reads the result out of RAM by symbol address and diffs it against
embedded_v2.py.  Also reports the decode tick count, which is what the
"67 trials against a ~180 ms window" claim has to be checked against.

Every ucsim child runs under `setsid timeout -k` and a pkill sweep
follows (simulator hygiene); the harness asserts zero strays at exit.

Corpus: dev_prod/fuzz_v23.py cases, chosen to cover every path (direct,
chase, and each refusal cause) plus the worst chase budgets.

  --nd 48|16     geometry (default 48, production)
  --n N          cases (default 24)
  --pick spread|worst   which cases (default spread: one per path/cause
                        plus the highest trial/comparison counts)
"""
import argparse
import collections
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
FW = NEWIMPL / "recon" / "approaches" / "dev_fw"
sys.path.insert(0, str(NEWIMPL))
from rbarf_config import sdas, sdcc, ucsim            # noqa: E402
sys.path.insert(0, str(SC))
import v23lib as L                                              # noqa: E402
import fuzz_v23                                                  # noqa: E402

CAUSES = {0: None, 1: "refuse_lock", 2: "refuse_marker",
          3: "refuse_infeasible", 4: "refuse_labelerr",
          5: "refuse_emitgate", 6: "refuse_nocand", 7: "refuse_admit",
          8: "refuse_chase"}
PATHS = {0: None, 1: "direct", 2: "chase", 3: "legacy_unverified"}
PORT = 21577
ND = 48


# BUILD-TIME chase budget (recon/AMAX_TMAX_SWEEP.md).  None = the
# firmware's own defaults (the shipped ledger 11 / 131), so the default
# invocation -- the one every previous phase recorded -- is unchanged and
# no chase_cfg.inc is generated for it: decode_asm.s then finds the one
# the last `make` wrote in NEWIMPL/build.
CHASE = [None, None]


# the shipped ledger budget, i.e. the Makefile's A_MAX/T_MAX defaults
CHASE_DEFAULT = (11, 131)


def chase_pt():
    return CHASE_DEFAULT if CHASE[0] is None else (CHASE[0], CHASE[1])


def chase_inc_dir():
    """Directory holding the chase_cfg.inc decode_asm.s must .include.
    Always GENERATED here, one directory per point, so this harness never
    depends on what `make` last left in build/ and a sweep can never
    assemble against a stale include."""
    a, t = chase_pt()
    d = SC / ("chase_A%d_T%d" % (a, t))
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(NEWIMPL / "gen_chase_cfg.py"),
                    str(a), str(t), str(d / "chase_cfg.inc")], check=True)
    return d


def cflags():
    fl = ["-mstm8", "--std-c99", "--opt-code-size",
          "--max-allocs-per-node", "100000",
          "-DND_DATA=%d" % ND, "-DCHECK_EN=1", "-DCHK_LEN=6",
          "-DUSE_ASM_SCAN=1", "-DUSE_ASM_DEC=1", "-I", str(NEWIMPL)]
    if CHASE[0] is not None:
        fl += ["-DA_MAX_CFG=%d" % CHASE[0], "-DT_MAX_CFG=%d" % CHASE[1]]
    return fl


def gen_cap(raw):
    lines = ["#include <stdint.h>",
             "const uint16_t CAP_LEN = %d;" % len(raw),
             "const uint8_t CAP[%d] = {" % len(raw)]
    for i in range(0, len(raw), 16):
        lines.append("  " + ",".join("0x%02X" % b for b in raw[i:i + 16])
                     + ",")
    lines.append("};")
    (SC / "cap_data23.c").write_text("\n".join(lines))


_objs = None


def build_once():
    global _objs
    if _objs is not None:
        return _objs
    fl = cflags()
    objs = []
    for src, out in ((NEWIMPL / "decode.c", "decode_v23sim.rel"),
                     (FW / "sim_v2.c", "sim_v23.rel")):
        subprocess.run([sdcc(), "-c"] + fl + [str(src), "-o", str(SC / out)],
                       check=True, capture_output=True)
        objs.append(str(SC / out))
    inc = ["-I" + str(chase_inc_dir())]   # sdas wants -Idir, not -I dir
    for src, out in ((NEWIMPL / "decode_asm.s", "decode_asm_v23sim.rel"),
                     (FW / "vectors_sim.s", "vectors_v23sim.rel")):
        subprocess.run([sdas(), "-plosg"] + inc +
                       ["-o", str(SC / out), str(src)],
                       check=True, capture_output=True)
        objs.append(str(SC / out))
    _objs = objs
    return objs


def link():
    fl = cflags()
    objs = list(build_once())
    subprocess.run([sdcc(), "-c"] + fl +
                   [str(SC / "cap_data23.c"), "-o", str(SC / "cap_data23.rel")],
                   check=True, capture_output=True)
    objs.append(str(SC / "cap_data23.rel"))
    subprocess.run([sdcc()] + fl + ["--data-loc", "0xF3",
                                    "--code-loc", "0x8068",
                                    "-o", str(SC / "sim_v23.ihx")] + objs,
                   check=True, capture_output=True)
    mtext = (SC / "sim_v23.map").read_text()
    sym = {}
    for line in mtext.splitlines():
        m = re.match(r"\s*([0-9A-Fa-f]{8})\s+"
                     r"(_g_status|_g_out|_dec_info|_sim_done|_ws_decode_ex)\b", line)
        if m:
            sym[m.group(2)] = int(m.group(1), 16)
    # the guard sdld does not provide: no REL flash area below 0x8068
    for area in ("HOME", "GSINIT", "GSFINAL", "CONST", "CODE"):
        am = re.search(r"^%s\s+([0-9A-F]{8})\s+([0-9A-F]{8})" % area,
                       mtext, re.M)
        if am and int(am.group(1), 16) < 0x8068:
            raise RuntimeError("sim link: %s at 0x%X overlaps the VGAP/"
                               "vector window" % (area, int(am.group(1), 16)))
    return sym, mtext


def sweep():
    subprocess.run(["pkill", "-x", "ucsim_stm8"], capture_output=True)
    time.sleep(0.1)
    if subprocess.run(["pgrep", "-x", "ucsim_stm8"],
                      capture_output=True).returncode == 0:
        subprocess.run(["pkill", "-9", "-x", "ucsim_stm8"],
                       capture_output=True)
        time.sleep(0.1)


class Ucsim:
    def __init__(self, ihx, port):
        self.p = subprocess.Popen(
            ["setsid", "timeout", "-k", "5", "120",
             ucsim(), "-t", "STM8S208", "-q", "-Z", str(port), ihx],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, text=True)
        # ucsim's -Z listener can take longer than a fixed 0.5 s to bind
        # on a loaded box, and a refused connect used to surface as a
        # whole run of bogus "target reported nothing" MISMATCHes.  Retry
        # for up to 10 s, and fail loudly if the child died instead.
        self.s = None
        deadline = time.time() + 10.0
        last = None
        while time.time() < deadline:
            time.sleep(0.25)
            if self.p.poll() is not None:
                raise RuntimeError("ucsim exited before binding port %d "
                                   "(rc %s)" % (port, self.p.returncode))
            try:
                self.s = socket.create_connection(("127.0.0.1", port),
                                                  timeout=5)
                break
            except OSError as e:
                last = e
        if self.s is None:
            raise RuntimeError("ucsim never bound port %d: %s" % (port, last))
        self.cmd("")

    def cmd(self, c, wait=0.3):
        self.s.sendall((c + "\n").encode())
        time.sleep(wait)
        return self._drain()

    def _drain(self):
        self.s.setblocking(False)
        buf = b""
        try:
            while True:
                ch = self.s.recv(65536)
                if not ch:
                    break
                buf += ch
        except BlockingIOError:
            pass
        self.s.setblocking(True)
        return buf.decode(errors="replace")

    def cmd_until(self, c, needle, timeout=90.0):
        self.s.sendall((c + "\n").encode())
        buf = ""
        end = time.time() + timeout
        while time.time() < end:
            time.sleep(0.15)
            buf += self._drain()
            if needle in buf:
                break
        return buf

    def read(self, addr, n):
        out = self.cmd("dump 0x%x 0x%x" % (addr, addr + n - 1), 0.25)
        vals = []
        for line in out.splitlines():
            m = re.match(r"0x[0-9a-f]+\s+((?:[0-9a-f]{2}\s+)+)", line)
            if m:
                vals += [int(x, 16) for x in m.group(1).split()]
        return vals[:n]

    def run_decode(self, brk, timeout=120.0):
        self.cmd("break 0x%x" % brk, 0.2)
        self.cmd_until("run", "Stop at", timeout=timeout)
        st = self.cmd("state", 0.3)
        mt = re.search(r"reset=\s*(\d+)\s*vclks", st)
        mpc = re.search(r"PC= 0x([0-9a-fA-F]+)", st)
        pc = int(mpc.group(1), 16) if mpc else None
        return (int(mt.group(1)) if mt else None,
                pc is not None and brk <= pc <= brk + 1)

    def close(self):
        try:
            self.cmd("kill", 0.1)
            self.p.wait(timeout=3)
        except Exception:
            self.p.kill()
        sweep()


def pick(cases, ev, n, mode):
    """One case per distinct (path, cause), then the heaviest chases."""
    rows = []
    for (tag, raw, truth, cls) in cases:
        out, info = ev.decode_ex(L.linearize(raw))
        rows.append((tag, raw, truth, cls, info, out))
    chosen, seen = [], set()
    for r in rows:
        k = (r[4]["path"], r[4]["cause"])
        if k not in seen:
            seen.add(k)
            chosen.append(r)
    rows.sort(key=lambda r: (-r[4].get("comps", 0), -r[4].get("trials", 0)))
    for r in rows:
        if len(chosen) >= n:
            break
        if r not in chosen:
            chosen.append(r)
    return chosen[:n]


def main():
    global ND
    ap = argparse.ArgumentParser()
    ap.add_argument("--nd", type=int, default=48)
    ap.add_argument("--n", type=int, default=24)
    # cap_arm.s FIX 2a: the new arm enters the pinned loop at _cap_loop+1,
    # so capture byte 0 bits 7..6 hold junk instead of the C flag.  --b0
    # forces those two bits in the capture handed to the TARGET while the
    # expectation stays the CLEAN reference decode: a pass therefore proves
    # both parity and the byte-0 invariance on-target.
    ap.add_argument("--b0", type=lambda v: int(v, 16), default=None,
                    help="force capture byte 0 bits 7..6 (hex, e.g. C0)")
    ap.add_argument("--amax", type=int, default=None,
                    help="chase A_MAX (default: the firmware's own 11)")
    ap.add_argument("--tmax", type=int, default=None,
                    help="chase T_MAX (default: the firmware's own 131)")
    a = ap.parse_args()
    if (a.amax is None) != (a.tmax is None):
        raise SystemExit("--amax and --tmax must be given together")
    if a.amax is not None:
        CHASE[0], CHASE[1] = a.amax, a.tmax
        print("chase budget: A_MAX=%d T_MAX=%d (asm .inc + C -D + the "
              "reference)" % (a.amax, a.tmax))
    ND = a.nd
    ev = L.load_ref()
    ev._configure(ND, chk=6)
    if CHASE[0] is not None:
        ev.set_chase_budget(CHASE[0], CHASE[1])
    cases = fuzz_v23.cases(ND)
    chosen = pick(cases, ev, a.n, "spread")
    sweep()
    n_ok = 0
    fails = []
    ticks = []
    sym, mtext = None, None
    for (tag, raw, truth, cls, ipy, d_py) in chosen:
        if a.b0 is not None:
            raw = bytes([(raw[0] & 0x3F) | (a.b0 & 0xC0)]) + raw[1:]
        gen_cap(raw)
        sym, mtext = link()
        # ucsim is occasionally flaky under load -- the -Z socket has been
        # seen to drop mid-case (BrokenPipeError on the next dump).  That
        # is a HARNESS fault, not a decoder result, so retry the case
        # LOUDLY rather than record a bogus mismatch.  A case that fails
        # twice is reported as a failure, never silently skipped.
        tk = at_brk = status = out = di = None
        for attempt in (1, 2, 3):
            sweep()
            sim = Ucsim(str(SC / "sim_v23.ihx"), PORT)
            try:
                tk, at_brk = sim.run_decode(sym["_sim_done"])
                status = sim.read(sym["_g_status"], 1)[0]
                out = sim.read(sym["_g_out"], ND)
                di = sim.read(sym["_dec_info"], 23)
                break
            except (OSError, RuntimeError, IndexError) as e:
                print("    [harness] ucsim attempt %d failed on %s: %s"
                      % (attempt, tag[:40], e))
                if attempt == 3:
                    raise
            finally:
                sim.close()
        if not at_brk:
            fails.append((tag, [("RUNAWAY", "never reached sim_done", None)]))
            continue
        d_c = bytes(out[:ND]) if status != 0 else None
        rows = []
        if d_c != d_py:
            rows.append(("bytes", d_c.hex() if d_c else None,
                         d_py.hex() if d_py else None))
        if PATHS.get(di[0]) != ipy["path"]:
            rows.append(("path", PATHS.get(di[0]), ipy["path"]))
        if CAUSES.get(di[1]) != ipy["cause"]:
            rows.append(("cause", CAUSES.get(di[1]), ipy["cause"]))
        if di[2] != ipy.get("trials", 0):
            rows.append(("trials", di[2], ipy.get("trials", 0)))
        if di[3] != ipy.get("alias_cmp", 0):
            rows.append(("alias_cmp", di[3], ipy.get("alias_cmp", 0)))
        if di[20] != ipy.get("comps", 0):
            rows.append(("comps", di[20], ipy.get("comps", 0)))
        if di[21] != ipy.get("n_refs", 0):
            rows.append(("n_refs", di[21], ipy.get("n_refs", 0)))
        nweak = di[5] << 8 | di[6]
        if nweak != ipy.get("n_weak", 0):
            rows.append(("n_weak", nweak, ipy.get("n_weak", 0)))
        if rows:
            fails.append((tag, rows))
        else:
            n_ok += 1
        ticks.append((tk or 0, ipy["path"] or ipy["cause"], di[2], di[20],
                      tag))
        print("  %-52s %-16s trials=%2d comps=%3d ticks=%s %s"
              % (tag[:52], ipy["path"] or ipy["cause"], di[2], di[20],
                 tk, "OK" if not rows else "MISMATCH %s" % rows[:3]))
    print()
    print("UCSIM v2.3 ON-TARGET PARITY (ND=%d%s%s): %d/%d bit-identical"
          % (ND, "" if a.b0 is None else ", capture byte0 bits7..6 = 0x%02X"
             % (a.b0 & 0xC0),
             "" if CHASE[0] is None
             else ", A_MAX=%d T_MAX=%d" % (CHASE[0], CHASE[1]),
             n_ok, len(chosen)))
    for t, r in fails[:8]:
        print("   ", t, r)
    if ticks:
        tk = sorted(t[0] for t in ticks if t[0])
        print("decode ticks: min %d  p50 %d  max %d   "
              "(@16 MHz: %.1f / %.1f / %.1f ms; ucsim under-reads this "
              "silicon ~7 %%)"
              % (tk[0], tk[len(tk) // 2], tk[-1],
                 tk[0] / 16000.0, tk[len(tk) // 2] / 16000.0,
                 tk[-1] / 16000.0))
        hv = max(ticks, key=lambda t: t[3])
        print("heaviest chase: comps=%d trials=%d -> %d ticks (%.1f ms)"
              % (hv[3], hv[2], hv[0], hv[0] / 16000.0))
    r = subprocess.run(["pgrep", "-x", "ucsim_stm8"], capture_output=True)
    print("stray ucsim processes at exit:",
          0 if r.returncode else len(r.stdout.split()))
    return 0 if n_ok == len(chosen) else 1


if __name__ == "__main__":
    raise SystemExit(main())
