#!/usr/bin/env python3
"""Comprehensive SINGLE-SHOT acceptance suite on real hardware.

Every payload the project has ever tested, expressed at production
geometry (48 data bytes -> 60-byte v2.3 frame = 20 LEDs), sent to the
device EXACTLY ONCE per pass.  The rule is strict: a frame that does not
latch on that one try -- refused, silent, or (worst) accepted with wrong
bytes -- is a FAILURE for that pattern in that pass.  No retries.

Families:
  main-ext   the 18 bring-up stress patterns (zeros/ones/aa/55/lone1/msb1/
             count/impulses/blocks/nibbles/sparse/dense/runs/edges/rnd1-3)
             regenerated at 48 bytes with their natural generators
  val-ext    the 12 held-out validation patterns, likewise
  prod       the 10 production gate payloads (bench/drive_prod.py)
  klipper    the 17 Klipper macro cases (bench/test_klipper_macro.py)
  demo       the 16 demo-reel scenes (bench/demo.py)
Duplicate byte patterns are merged (first name wins).

Requires a VERBOSE production image (the V: line is what lets a delivered
frame be byte-checked against ground truth, not just CRC-accepted).

  python3 bench/suite_singleshot.py --ihx build/rbarf_prod_verbose.ihx --passes 3
  python3 bench/suite_singleshot.py --list
"""

import argparse
import json
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJ = _HERE.parent
sys.path.insert(0, str(_PROJ))
sys.path.insert(0, str(_HERE))
from rbarf_config import import_testprobe, probe_port      # noqa: E402
TestProbe = import_testprobe()
from patterns import (PATTERNS, VAL_PATTERNS, _lcg_bytes,   # noqa: E402
                      build_payload_v23, frame_v23)

PIN_POWER, POWER_ON_LEVEL = 28, 1
PIN_UART_RX, PIN_UART_TX, PIN_WS2812, BAUD = 1, 0, 29, 9600
GAP = 0.50            # well clear of the ~180 ms decode blind window
ND = 48


# ---------------------------------------------------------- pattern set
def _ext(name, p16):
    """48-byte version of a 16-byte bring-up pattern, by its generator."""
    if len(set(p16)) == 1:                       # byte repeat
        return bytes([p16[0]] * ND)
    if name == "count":
        return bytes(range(ND))
    if name == "impulse_hi":
        return bytes([0] * 21 + [0xFF] + [0] * 26)
    if name == "impulse_lo":
        return bytes([0xFF] * 21 + [0] + [0xFF] * 26)
    if name in ("blocks", "nibbles", "runs", "edges", "vchecker"):
        return bytes(list(p16[:2]) * (ND // 2))
    if name.startswith(("rnd", "vrnd")):
        seeds = {"rnd1": 1, "rnd2": 2, "rnd3": 3, "vrnd4": 11, "vrnd5": 17,
                 "vrnd6": 23, "vrnd7": 31, "vrnd8": 47}
        return _lcg_bytes(seeds[name], ND)
    if name == "vgray":
        return bytes((i ^ (i >> 1)) & 0xFF for i in range(ND))
    if name == "vwalk1":
        return bytes((1 << (i % 8)) for i in range(ND))
    if name == "vwalkz":
        return bytes(0xFF ^ (1 << (i % 8)) for i in range(ND))
    if name == "vprime":
        ps, n = [], 2
        while len(ps) < ND:
            if all(n % q for q in ps if q * q <= n):
                ps.append(n)
            n += 1
        return bytes(p & 0xFF for p in ps)
    return (p16 * 3)[:ND]                        # generic tile


def _module_prefix(path, stop="\ndef main("):
    """exec a bench script up to its main() so its tables are importable
    without running it."""
    src = path.read_text()
    i = src.find(stop)
    ns = {"__name__": "suite_import", "__file__": str(path)}
    exec(compile(src[:i] if i > 0 else src, str(path), "exec"), ns)
    return ns


def build_suite():
    suite, seen = [], {}

    def add(fam, name, data):
        assert len(data) == ND, (name, len(data))
        key = bytes(data)
        if key in seen:
            return
        seen[key] = name
        suite.append((fam, name, key))

    for n, p in PATTERNS.items():
        add("main-ext", n, _ext(n, p))
    for n, p in VAL_PATTERNS.items():
        add("val-ext", n, _ext(n, p))
    dp = _module_prefix(_HERE / "drive_prod.py")
    for n, d in dp["FRAMES"]:
        add("prod", n, d)
    km = _module_prefix(_HERE / "test_klipper_macro.py")
    for n, _gcode, d in km["build_cases"]():
        add("klipper", n, d)
    dm = _module_prefix(_HERE / "demo.py", stop="\nclass Lines:")
    for n, _desc, d in dm["REEL"]:
        add("demo", n, d)
    return suite


# ---------------------------------------------------------- UART lines
class Lines:
    def __init__(self):
        self.buf, self.lines = bytearray(), []
        self.cond = threading.Condition()
        self.banners = 0

    def feed(self, data):
        with self.cond:
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                ln = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[:nl + 1]
                if ln:
                    s = ln.decode("ascii", "replace")
                    if s.startswith("RBARF-P"):
                        self.banners += 1
                    self.lines.append((time.monotonic(), s))
            self.cond.notify_all()

    def take(self, prefixes, timeout):
        dl = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (t, s) in enumerate(self.lines):
                    if s.startswith(prefixes):
                        del self.lines[:i + 1]
                        return s
                left = dl - time.monotonic()
                if left <= 0:
                    return None
                self.cond.wait(left)

    def clear(self):
        with self.cond:
            self.lines.clear()
            self.buf.clear()        # BOTH buffers (see demo.py)


# ---------------------------------------------------------- one frame
def send_once(probe, lines, frame, truth):
    """-> (verdict, detail).  verdict: PASS | REFUSE | WRONG | SILENT | PROTO"""
    lines.clear()
    probe.ws2812_write(frame)
    dec = lines.take(("D:",), 1.5)
    if dec is None:
        return "SILENT", "no report"
    try:
        _, st, eps = dec.split(":")
    except ValueError:
        return "PROTO", dec[:40]
    if st in ("O", "C"):
        ver = lines.take(("V:",), 3.0)
        if ver is None:
            return "PROTO", "no V: after accept"
        if ver[2:].lower() == truth.hex():
            return "PASS", f"{'direct' if st == 'O' else 'chase'} eps={eps}"
        return "WRONG", f"emitted {ver[2:34]}... eps={eps}"
    if st.startswith("R"):
        return "REFUSE", f"{st} eps={eps}"
    return "PROTO", dec[:40]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ihx", help="verbose production image to flash first")
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260908)
    ap.add_argument("--tag", default=None, help="label for the results file")
    ap.add_argument("--port", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    suite = build_suite()
    if args.list:
        fam = {}
        for f, n, d in suite:
            fam.setdefault(f, []).append(n)
        for f, ns in fam.items():
            print(f"{f:9s} {len(ns):3d}: {', '.join(ns)}")
        print(f"total {len(suite)} unique payloads")
        return

    tag = args.tag or (Path(args.ihx).stem if args.ihx else "current")
    if args.ihx:
        print(f"[suite] flashing {args.ihx}")
        r = subprocess.run([sys.executable, str(_PROJ / "flash.py"),
                            "--ihx", args.ihx, "flash-only"],
                           cwd=str(_PROJ), timeout=180)
        if r.returncode != 0:
            sys.exit("[suite] flash failed")

    port = probe_port(args.port, required=True)
    lines = Lines()
    results = []          # (pass, family, name, verdict, detail)
    rnd = random.Random(args.seed)
    with TestProbe(port) as probe:
        probe.on_uart_rx = lines.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)
        probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
        time.sleep(2.0)
        probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
        banner = lines.take(("RBARF",), 15.0)
        print(f"[suite] target: {banner}")
        if not banner or "RBARF-P" not in banner:
            sys.exit("[suite] production firmware not running -- use --ihx")
        time.sleep(0.5)
        lines.clear()
        banners0 = lines.banners

        n = len(suite)
        print(f"[suite] {n} payloads x {args.passes} passes, ONE frame each, "
              f"{GAP*1000:.0f} ms spacing, shuffled (seed {args.seed})\n")
        for p in range(1, args.passes + 1):
            order = suite[:]
            rnd.shuffle(order)
            fails = 0
            for fam, name, data in order:
                fr = frame_v23(build_payload_v23(data))
                verdict, detail = send_once(probe, lines, fr, data)
                results.append((p, fam, name, verdict, detail))
                if verdict != "PASS":
                    fails += 1
                    print(f"  pass {p}  FAIL  {fam:8s} {name:20s} {verdict:7s} {detail}")
                time.sleep(GAP)
            print(f"[suite] pass {p}: {n - fails}/{n} first-try  "
                  f"({fails} failure{'s' if fails != 1 else ''})")
        resets = lines.banners - banners0

    # ------------------------------------------------------ summary
    total = len(results)
    passed = sum(1 for r in results if r[3] == "PASS")
    by_v = {}
    for r in results:
        by_v[r[3]] = by_v.get(r[3], 0) + 1
    print(f"\n[suite] {tag}: {passed}/{total} first-try over {args.passes} "
          f"passes = {100*passed/total:.1f}%   verdicts {by_v}   "
          f"MCU resets {resets}")
    fams = {}
    for p, fam, name, v, d in results:
        fams.setdefault(fam, [0, 0])
        fams[fam][1] += 1
        fams[fam][0] += (v == "PASS")
    print("  per family:")
    for fam, (ok, tot) in fams.items():
        print(f"    {fam:9s} {ok:3d}/{tot:<3d} {100*ok/tot:5.1f}%")
    per = {}
    for p, fam, name, v, d in results:
        per.setdefault((fam, name), []).append(v)
    flaky = {k: v for k, v in per.items() if any(x != "PASS" for x in v)}
    if flaky:
        print("  patterns with any first-try failure:")
        for (fam, name), vs in sorted(flaky.items()):
            print(f"    {fam:8s} {name:20s} {' '.join(x[:6] for x in vs)}")
    else:
        print("  every pattern latched first try in every pass")
    wrong = [r for r in results if r[3] == "WRONG"]
    print(f"  WRONG (accepted with bad bytes): {len(wrong)}"
          + ("  <-- CATASTROPHIC" if wrong else ""))

    out = Path(args.out) if args.out else (
        _PROJ / "recon" / "approaches" / "dev_suite" / f"singleshot_{tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "tag": tag, "ihx": args.ihx, "passes": args.passes, "seed": args.seed,
        "gap_s": GAP, "resets": resets,
        "suite": [{"family": f, "name": n, "data": d.hex()} for f, n, d in suite],
        "results": [{"pass": p, "family": f, "name": n, "verdict": v,
                     "detail": d} for p, f, n, v, d in results],
    }, indent=1))
    print(f"  saved {out}")


if __name__ == "__main__":
    main()
