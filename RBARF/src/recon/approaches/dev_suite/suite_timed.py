#!/usr/bin/env python3
"""TIMED / SOAK copy of bench/suite_singleshot.py -- NOT the acceptance metric.

`bench/suite_singleshot.py` is the acceptance metric and must stay
byte-identical for every image, so it records no timing.  This is a COPY of
it that adds three things and changes nothing else about how a frame is put
on the wire or scored:

  1. per-frame DECODE TIME, by exactly bench/drive_prod.py's decomposition
     decode_ms = (t_Dline_complete - t_write_start)*1e3
                 - FRAME_TX_MS - CAPTURE_MS - transit_ms
     so the numbers are directly comparable with PROD_CLOSURE SS16.7 /
     SS20.4 (the "170 ms baseline").
  2. `--only` payload selection + `--passes N`, so the corruption-prone
     subset (the pale / 1-dense payloads and every random one) can be soaked
     for hundreds of frames looking for a WRONG emission.
  3. the eps of every report, and the raw timestamps, in the saved JSON.

The pattern set, the frame construction, the 500 ms gap, the shuffle and the
PASS/REFUSE/WRONG/SILENT/PROTO verdicts are the suite's, unmodified.

  python3 recon/approaches/dev_suite/suite_timed.py --tag A16_T192_timed
  python3 recon/approaches/dev_suite/suite_timed.py --only soak --passes 17 \
          --tag A16_T192_soak
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
_PROJ = next(p for p in _HERE.parents if (p / "rbarf_config.py").is_file())
_BENCH = _PROJ / "bench"
sys.path.insert(0, str(_PROJ))
sys.path.insert(0, str(_BENCH))
from rbarf_config import import_testprobe, probe_port      # noqa: E402
TestProbe = import_testprobe()
from patterns import (PATTERNS, VAL_PATTERNS, _lcg_bytes,   # noqa: E402
                      build_payload_v23, frame_v23)

PIN_POWER, POWER_ON_LEVEL = 28, 1
PIN_UART_RX, PIN_UART_TX, PIN_WS2812, BAUD = 1, 0, 29, 9600
GAP = 0.50            # the suite's gap, unchanged
ND = 48

# --- bench/drive_prod.py's timing constants, verbatim -----------------
CHAR_MS = 10.0 / BAUD * 1000.0                              # 8N1
FACTORY_EPS = -0.0107
CAPTURE_MS = 288 * 40 / 16e6 * 1e3 / (1.0 + FACTORY_EPS)    # 288 loops
FRAME_TX_MS = 60 * 8 * 1.25e-3                              # 0.60 ms

# The corruption-prone subset: every payload whose 1-density is >= 45 %
# (the pale / merged-1 stress cases -- `ones`, `impulse_lo`, `vwalkz`,
# `runs`, `dense`, `full`, `all_ff_base` and the 50 % tilings) plus every
# random payload.  These are the carriers the sweep named for R7/R8 and
# the ones a bigger A_MAX re-admits.
SOAK_NAMES = [
    "ones", "impulse_lo", "vwalkz", "runs", "dense", "full", "all_ff_base",
    "rnd1", "rnd2", "rnd3", "vrnd4", "vrnd5", "vrnd6", "vrnd7", "vrnd8",
    "rnd", "rnd_colors1", "rnd_colors2", "vprime", "vchecker",
]


# ---------------------------------------------------------- pattern set
# (identical to bench/suite_singleshot.py)
def _ext(name, p16):
    if len(set(p16)) == 1:
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
    return (p16 * 3)[:ND]


def _module_prefix(path, stop="\ndef main("):
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
    dp = _module_prefix(_BENCH / "drive_prod.py")
    for n, d in dp["FRAMES"]:
        add("prod", n, d)
    km = _module_prefix(_BENCH / "test_klipper_macro.py")
    for n, _gcode, d in km["build_cases"]():
        add("klipper", n, d)
    dm = _module_prefix(_BENCH / "demo.py", stop="\nclass Lines:")
    for n, _desc, d in dm["REEL"]:
        add("demo", n, d)
    return suite


# ---------------------------------------------------------- UART lines
class Lines:
    """the suite's Lines, plus the arrival timestamps drive_prod.py keeps."""

    def __init__(self):
        self.buf, self.lines = bytearray(), []      # (t_start, t_done, str)
        self.cond = threading.Condition()
        self.banners = 0
        self.t_chunk0 = None

    def feed(self, data):
        now = time.monotonic()
        with self.cond:
            if not self.buf:
                self.t_chunk0 = now
            t0 = self.t_chunk0
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
                    self.lines.append((t0, now, s))
                t0 = now
                self.t_chunk0 = now
            self.cond.notify_all()

    def take(self, prefixes, timeout):
        dl = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (ts, td, s) in enumerate(self.lines):
                    if s.startswith(prefixes):
                        del self.lines[:i + 1]
                        return ts, td, s
                left = dl - time.monotonic()
                if left <= 0:
                    return None, None, None
                self.cond.wait(left)

    def clear(self):
        with self.cond:
            self.lines.clear()
            self.buf.clear()


# ---------------------------------------------------------- one frame
def send_once(probe, lines, frame, truth):
    """-> (verdict, detail, timing dict).  Verdicts are the suite's."""
    lines.clear()
    t0 = time.monotonic()
    probe.ws2812_write(frame)
    t1 = time.monotonic()
    ts_d, td_d, dec = lines.take(("D:",), 1.5)
    tm = {"uplink_ms": (t1 - t0) * 1e3}
    if dec is None:
        return "SILENT", "no report", tm
    lat_ms = (td_d - t0) * 1e3
    transit_ms = (len(dec) + 2) * CHAR_MS
    tm.update(latency_ms=lat_ms, transit_ms=transit_ms,
              decode_ms=lat_ms - FRAME_TX_MS - CAPTURE_MS - transit_ms,
              d_line=dec)
    try:
        _, st, eps = dec.split(":")
    except ValueError:
        return "PROTO", dec[:40], tm
    tm["status"], tm["eps"] = st, eps
    if st in ("O", "C"):
        ts_v, td_v, ver = lines.take(("V:",), 3.0)
        if ver is None:
            return "PROTO", "no V: after accept", tm
        tm["v_done_ms"] = (td_v - t0) * 1e3
        if ver[2:].lower() == truth.hex():
            return "PASS", f"{'direct' if st == 'O' else 'chase'} eps={eps}", tm
        return "WRONG", f"emitted {ver[2:34]}... eps={eps}", tm
    if st.startswith("R"):
        return "REFUSE", f"{st} eps={eps}", tm
    return "PROTO", dec[:40], tm


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ihx", help="verbose production image to flash first")
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260908)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--port", default=None)
    ap.add_argument("--only", default=None,
                    help="'soak' for the corruption-prone subset, or a "
                         "comma-separated list of payload names")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    suite = build_suite()
    if args.only:
        want = (SOAK_NAMES if args.only == "soak"
                else [s.strip() for s in args.only.split(",")])
        have = {n for _f, n, _d in suite}
        missing = [w for w in want if w not in have]
        if missing:
            sys.exit(f"[timed] unknown payload(s): {missing}")
        suite = [(f, n, d) for (f, n, d) in suite if n in want]

    tag = args.tag or (Path(args.ihx).stem if args.ihx else "current")
    if args.ihx:
        print(f"[timed] flashing {args.ihx}")
        r = subprocess.run([sys.executable, str(_PROJ / "flash.py"),
                            "--ihx", args.ihx, "flash-only"],
                           cwd=str(_PROJ), timeout=180)
        if r.returncode != 0:
            sys.exit("[timed] flash failed")

    port = probe_port(args.port, required=True)
    lines = Lines()
    results = []
    rnd = random.Random(args.seed)
    with TestProbe(port) as probe:
        probe.on_uart_rx = lines.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)
        probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
        time.sleep(2.0)
        probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
        _ts, _td, banner = lines.take(("RBARF",), 15.0)
        print(f"[timed] target: {banner}")
        if not banner or "RBARF-P" not in banner:
            sys.exit("[timed] production firmware not running -- use --ihx")
        time.sleep(0.5)
        lines.clear()
        banners0 = lines.banners

        n = len(suite)
        print(f"[timed] {n} payloads x {args.passes} passes = "
              f"{n*args.passes} frames, ONE frame each, {GAP*1000:.0f} ms "
              f"spacing, shuffled (seed {args.seed})\n")
        for p in range(1, args.passes + 1):
            order = suite[:]
            rnd.shuffle(order)
            fails = 0
            for fam, name, data in order:
                fr = frame_v23(build_payload_v23(data))
                verdict, detail, tm = send_once(probe, lines, fr, data)
                results.append({"pass": p, "family": fam, "name": name,
                                "verdict": verdict, "detail": detail, **tm})
                if verdict != "PASS":
                    fails += 1
                    print(f"  pass {p}  FAIL  {fam:8s} {name:20s} "
                          f"{verdict:7s} {detail}")
                if verdict == "WRONG":
                    print("  *** WRONG EMISSION -- HARD STOP CONDITION ***")
                time.sleep(GAP)
            print(f"[timed] pass {p}: {n - fails}/{n} first-try "
                  f"({fails} failure{'s' if fails != 1 else ''})")
        resets = lines.banners - banners0

    # ------------------------------------------------------ summary
    total = len(results)
    passed = sum(1 for r in results if r["verdict"] == "PASS")
    by_v = {}
    for r in results:
        by_v[r["verdict"]] = by_v.get(r["verdict"], 0) + 1
    print(f"\n[timed] {tag}: {passed}/{total} first-try = "
          f"{100*passed/total:.1f}%   verdicts {by_v}   MCU resets {resets}")

    dec = sorted((r["decode_ms"], r["name"], r["detail"])
                 for r in results if r.get("decode_ms") is not None)
    if dec:
        vals = [d[0] for d in dec]
        def q(f):
            return vals[min(len(vals) - 1, int(f * (len(vals) - 1) + 0.5))]
        print(f"  decode window over {len(vals)} reports: min {vals[0]:.1f} / "
              f"p50 {q(0.5):.1f} / p90 {q(0.9):.1f} / max {vals[-1]:.1f} ms")
        print("  the 8 longest decodes:")
        for v, nm, det in dec[-8:][::-1]:
            print(f"    {v:7.1f} ms  {nm:20s} {det}")
        ch = [d for d in dec if "chase" in d[2]]
        if ch:
            cv = [d[0] for d in ch]
            print(f"  chase-repaired ({len(cv)}): min {min(cv):.1f} / "
                  f"max {max(cv):.1f} ms")
        lat = [r["latency_ms"] for r in results if r.get("latency_ms")]
        print(f"  host latency (frame start -> D: complete) max "
              f"{max(lat):.1f} ms")
    wrong = [r for r in results if r["verdict"] == "WRONG"]
    print(f"  WRONG (accepted with bad bytes): {len(wrong)}"
          + ("  <-- CATASTROPHIC" if wrong else ""))

    out = Path(args.out) if args.out else (_HERE / f"timed_{tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "tag": tag, "ihx": args.ihx, "passes": args.passes, "seed": args.seed,
        "gap_s": GAP, "resets": resets, "only": args.only,
        "timing_model": {"char_ms": CHAR_MS, "capture_ms": CAPTURE_MS,
                         "frame_tx_ms": FRAME_TX_MS,
                         "note": "bench/drive_prod.py decomposition"},
        "suite": [{"family": f, "name": n, "data": d.hex()} for f, n, d in suite],
        "results": results,
    }, indent=1))
    print(f"  saved {out}")


if __name__ == "__main__":
    main()
