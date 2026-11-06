#!/usr/bin/env python3
"""Task-1 validation: run decode.c (+ optionally scan.s) IN UCSIM over real
captures and diff every emitted byte + path/cause against embedded_v2.py.

This is the on-target equivalent of parity_host.py: the exact SDCC-built
STM8 image the firmware ships, executed instruction-by-instruction in
ucsim_stm8, its result read back from RAM by symbol address, compared to
the validated Python reference.  Mirrors archive/investigations/dev_embedded/eval_c.py's role for
v1 but runs the code in-simulator rather than as a host .so.

Per the task: >= 20 captures from captures_v21.json + >= 10 from
captures_trim.json.  captures_v21 uses the CHECK_EN=1 build (full chase);
captures_trim uses CHECK_EN=0 (legacy v2.0 geometry, chase off) since
those frames carry no check block.  data/captures_val.json is never read.

  --scan c|asm   which sample scanner to build in (default: both)
  --n21 N        captures_v21 count (default 24)
  --ntrim N      captures_trim count (default 12)
  --ncap N       capture bytes embedded (default 256 = firmware buffer)
  --cycles       also report decode ticks (state vclks) per capture

Usage: python3 ucsim_bitexact.py
"""
import argparse
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NEWIMPL = ROOT.parent
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402
import importlib.util
spec = importlib.util.spec_from_file_location(
    "embedded_v2", ROOT / "approaches" / "embedded_v2.py")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

CAUSES = {0: None, 1: "refuse_lock", 2: "refuse_marker",
          3: "refuse_infeasible", 4: "refuse_labelerr", 5: "refuse_emitgate",
          6: "refuse_nocand", 7: "refuse_admit", 8: "refuse_chase"}
PATHS = {0: None, 1: "direct", 2: "chase", 3: "legacy_unverified"}
PORT = 21500


def gen_cap(raw):
    lines = ["#include <stdint.h>",
             "const uint16_t CAP_LEN = %d;" % len(raw),
             "const uint8_t CAP[%d] = {" % len(raw)]
    for i in range(0, len(raw), 16):
        lines.append("  " + ",".join("0x%02X" % b for b in raw[i:i + 16]) + ",")
    lines.append("};")
    (HERE / "cap_data.c").write_text("\n".join(lines))


ASMDEC = False      # set by --asmdec: link decode_asm.s (USE_ASM_DEC=1)
ND_DATA = 16        # frame geometry (48 = production; smoke48.py sets it)
CHK = 4             # check-block bytes: 4 = v2.2 (default), 3 = the
                    # superseded v2.1 geometry (captures_v21*.json runs)


def _cflags(check_en, use_asm):
    # the shipped build's exact flags (Makefile PRODFLAGS/V21FLAGS + CFLAGS)
    fl = ["-mstm8", "--std-c99", "--opt-code-size",
          "--max-allocs-per-node", "100000",
          "-DND_DATA=%d" % ND_DATA,
          "-DCHECK_EN=%d" % (1 if check_en else 0),
          "-DUSE_ASM_SCAN=%d" % (1 if use_asm else 0),
          "-DUSE_ASM_DEC=%d" % (1 if ASMDEC else 0), "-I", str(NEWIMPL)]
    if check_en:
        fl.insert(7, "-DCHK_LEN=%d" % CHK)
    return fl


_cfg_objs = {}


def build_config(check_en, use_asm):
    """Compile decode.c + sim_v2.c (+ scan.s) once per configuration."""
    key = (check_en, use_asm, ND_DATA, CHK)
    if key in _cfg_objs:
        return _cfg_objs[key]
    cflags = _cflags(check_en, use_asm)
    tag = "%d%d_c%d" % (1 if check_en else 0, 1 if use_asm else 0, CHK)
    objs = []
    for src in ("decode.c", "sim_v2.c"):
        base = src[:-2]
        s = (NEWIMPL / src) if src == "decode.c" else (HERE / src)
        obj = HERE / ("%s_%s_%d.rel" % (base, tag, ND_DATA))
        subprocess.run(["sdcc", "-c"] + cflags + [str(s), "-o", str(obj)],
                       check=True, capture_output=True)
        objs.append(str(obj))
    if use_asm and not ASMDEC:
        subprocess.run(["sdasstm8", "-plosg", "-o",
                        str(HERE / "scan.rel"), str(NEWIMPL / "scan.s")],
                       check=True, capture_output=True)
        objs.append(str(HERE / "scan.rel"))
    if ASMDEC:
        subprocess.run(["sdasstm8", "-plosg", "-o",
                        str(HERE / "decode_asm.rel"),
                        str(NEWIMPL / "decode_asm.s")],
                       check=True, capture_output=True)
        objs.append(str(HERE / "decode_asm.rel"))
        # decode_asm relocates helpers into the vector gap (VGAP, ABS
        # 0x8004..0x8063): the link MUST use --code-loc 0x8068 like the
        # production image, and vectors_sim.s supplies the 0x8000 reset
        # vector SDCC's relocated table no longer covers.  Without this
        # the ABS VGAP bytes silently clobber GSINIT (sdld checks no
        # REL/ABS overlap) and the sim runs garbage as its startup.
        subprocess.run(["sdasstm8", "-plosg", "-o",
                        str(HERE / "vectors_sim.rel"),
                        str(HERE / "vectors_sim.s")],
                       check=True, capture_output=True)
        objs.append(str(HERE / "vectors_sim.rel"))
    _cfg_objs[key] = objs
    return objs


def build(check_en, use_asm):
    """Compile cap_data.c and link against the cached config objects."""
    cflags = _cflags(check_en, use_asm)
    objs = list(build_config(check_en, use_asm))
    subprocess.run(["sdcc", "-c"] + cflags +
                   [str(HERE / "cap_data.c"), "-o",
                    str(HERE / "cap_data.rel")], check=True,
                   capture_output=True)
    objs.append(str(HERE / "cap_data.rel"))
    link_extra = (["--data-loc", "0x100", "--code-loc", "0x8068"]
                  if ASMDEC else [])
    subprocess.run(["sdcc"] + cflags + link_extra +
                   ["-o", str(HERE / "sim_v2.ihx")] +
                   objs, check=True, capture_output=True)
    # symbol addresses from the map
    sym = {}
    mtext = (HERE / "sim_v2.map").read_text()
    for line in mtext.splitlines():
        m = re.match(r"\s*([0-9A-Fa-f]{8})\s+(_g_status|_g_out|_dec_info|_sim_done)\b", line)
        if m:
            sym[m.group(2)] = int(m.group(1), 16)
    if ASMDEC:
        # the guard sdld does not provide: no REL flash area below 0x8068
        # (the ABS VGAP block owns 0x8004..0x8063)
        for area in ("HOME", "GSINIT", "GSFINAL", "CONST", "CODE"):
            am = re.search(r"^%s\s+([0-9A-F]{8})\s+([0-9A-F]{8})" % area,
                           mtext, re.M)
            if am and int(am.group(1), 16) < 0x8068:
                raise RuntimeError("sim link: %s at 0x%X overlaps the "
                                   "VGAP/vector window" % (area,
                                   int(am.group(1), 16)))
    return sym


def sweep():
    """pkill sweep: zero stray simulators, checked (simulator hygiene)."""
    subprocess.run(["pkill", "-x", "ucsim_stm8"], capture_output=True)
    time.sleep(0.1)
    r = subprocess.run(["pgrep", "-x", "ucsim_stm8"], capture_output=True)
    if r.returncode == 0:
        subprocess.run(["pkill", "-9", "-x", "ucsim_stm8"],
                       capture_output=True)
        time.sleep(0.1)


class Ucsim:
    def __init__(self, ihx, port):
        # every ucsim child runs under setsid timeout -k (hygiene rule)
        self.p = subprocess.Popen(
            ["setsid", "timeout", "-k", "5", "120",
             "ucsim_stm8", "-t", "STM8S208", "-q", "-Z", str(port), ihx],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, text=True)
        time.sleep(0.5)
        self.s = socket.create_connection(("127.0.0.1", port), timeout=5)
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

    def cmd_until(self, c, needle, timeout=45.0):
        """Send c, poll the socket until `needle` appears or timeout."""
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

    def run_decode(self, brk=None, timeout=60.0):
        """Run to sim_done and STOP THERE, before the halt executes.

        brk = address of _sim_done (from the map).  A fetch breakpoint is
        deterministic and read-safe: every result byte is committed by
        then, and the CPU is parked, so memory reads cannot race any
        post-halt simulator behaviour.  (Waiting for the HALT message is
        NOT safe: a runaway image never halts, and reads at a timeout can
        see RAM the runaway has been trashing for seconds.)

        Returns (ticks, stopped_at_brk).  ticks is the vclk count when
        the state output carries one, else None.
        """
        if brk is not None:
            self.cmd("break 0x%x" % brk, 0.2)
        buf = self.cmd_until("run", "Stop at", timeout=timeout)
        st = self.cmd("state", 0.3)
        ticks = None
        mt = re.search(r"reset=\s*(\d+)\s*vclks", st)
        if mt:
            ticks = int(mt.group(1))
        mpc = re.search(r"PC= 0x([0-9a-fA-F]+)", st)
        pc = int(mpc.group(1), 16) if mpc else None
        at_brk = (brk is not None and pc is not None and
                  brk <= pc <= brk + 1)
        return ticks, at_brk

    def reset(self):
        self.cmd("reset", 0.3)
        self.cmd("pc 0x8000", 0.2)

    def close(self):
        try:
            self.cmd("kill", 0.1)
            self.p.wait(timeout=3)
        except Exception:
            self.p.kill()
        sweep()


def run_corpus(path, check_en, use_asm, count, ncap, want_cycles):
    v2._configure(ND_DATA, check=check_en, chk=CHK)
    _, caps = load_dataset(path)
    caps = caps[:count]
    n_ok = 0
    fails = []
    ticks_list = []
    for c in caps:
        raw = bytes.fromhex(c["capture"])[:ncap]
        gen_cap(raw)
        sym = build(check_en, use_asm)
        sim = Ucsim(str(HERE / "sim_v2.ihx"), PORT)
        try:
            ticks, at_brk = sim.run_decode(brk=sym.get("_sim_done"))
            status = sim.read(sym["_g_status"], 1)[0]
            out = sim.read(sym["_g_out"], ND_DATA)
            di = sim.read(sym["_dec_info"], 20)
        finally:
            sim.close()
        if not at_brk:
            fails.append(("%s r%s" % (c.get("pattern"), c.get("rep")),
                          [("RUNAWAY", "never reached sim_done", None)]))
            continue
        # decode dec_info struct (packed order from decode.h)
        path_v = di[0]
        cause_v = di[1]
        # bytes: emitted iff status != 0
        d_c = bytes(out[:ND_DATA]) if status != 0 else None
        # Python reference
        d_py, ipy = v2.decode_ex(linearize(raw.hex()))
        tag = "%s r%s" % (c.get("pattern"), c.get("rep"))
        if c.get("trim") is not None:
            tag = "trim%s %s" % (c["trim"], tag)
        rows = []
        if d_c != d_py:
            rows.append(("bytes", d_c.hex() if d_c else None,
                         d_py.hex() if d_py else None))
        if PATHS.get(path_v) != ipy["path"]:
            rows.append(("path", PATHS.get(path_v), ipy["path"]))
        if CAUSES.get(cause_v) != ipy["cause"]:
            rows.append(("cause", CAUSES.get(cause_v), ipy["cause"]))
        # full counter contract (decode.h field layout)
        cvals = {"trials": di[2], "alias_cmp": di[3], "chased": di[4],
                 "n_weak": (di[5] << 8) | di[6],
                 "n_tied": (di[7] << 8) | di[8],
                 "K": (di[9] << 8) | di[10],
                 "violations": di[13],
                 "infeasible": (di[14] << 8) | di[15],
                 "label_err": (di[16] << 8) | di[17]}
        tau_c = (di[11] << 8) | di[12]
        if tau_c >= 0x8000:
            tau_c -= 0x10000
        cvals["tau"] = tau_c
        for f, cv in cvals.items():
            pv = ipy.get(f, 0)
            if pv is None:
                pv = 0
            if f == "chased":
                cv, pv = bool(cv), bool(pv)
            if cv != pv:
                rows.append((f, cv, pv))
        if rows:
            fails.append((tag, rows))
        else:
            n_ok += 1
        if want_cycles and ticks is not None:
            ticks_list.append((tag, ticks))
    return n_ok, len(caps), fails, ticks_list


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", choices=("c", "asm", "both"), default="both")
    ap.add_argument("--n21", type=int, default=24)
    ap.add_argument("--ntrim", type=int, default=12)
    ap.add_argument("--ncap", type=int, default=256)
    ap.add_argument("--cycles", action="store_true")
    ap.add_argument("--asmdec", action="store_true",
                    help="link decode_asm.s (USE_ASM_DEC=1 target build)")
    args = ap.parse_args()
    global ASMDEC, CHK
    ASMDEC = args.asmdec
    data = NEWIMPL / "data"
    scans = [False, True] if args.scan == "both" else \
            [args.scan == "asm"]
    all_ok = True
    for use_asm in scans:
        label = "scan.s (asm)" if use_asm else "C scanner"
        print("=" * 68)
        print("UCSIM BIT-EXACTNESS -- %s" % label)
        print("=" * 68)
        CHK = 3                      # the v2.1 corpora: CHK_LEN=3 mode
        n1, t1, f1, tk1 = run_corpus(
            str(data / "captures_v21.json"), True, use_asm,
            args.n21, args.ncap, args.cycles)
        print("captures_v21.json   %2d/%2d bit-identical (bytes+path+cause,"
              " CHK_LEN=3 mode)" % (n1, t1))
        for tag, rows in f1:
            print("   MISMATCH", tag, rows)
        CHK = 4
        n2, t2, f2, tk2 = run_corpus(
            str(data / "captures_trim.json"), False, use_asm,
            args.ntrim, args.ncap, args.cycles)
        print("captures_trim.json  %2d/%2d bit-identical (legacy v2.0)"
              % (n2, t2))
        for tag, rows in f2:
            print("   MISMATCH", tag, rows)
        ok = (n1 == t1 and n2 == t2)
        all_ok &= ok
        print("  -> %s : %s" % (label, "PASS" if ok else "FAIL"))
        if args.cycles and (tk1 or tk2):
            allt = [t for _, t in tk1 + tk2]
            print("  decode ticks (ucsim, documented counts): min %d max %d "
                  "mean %d over %d decodes"
                  % (min(allt), max(allt), sum(allt) // len(allt), len(allt)))
    print()
    print("TASK 1 UCSIM VALIDATION:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
