#!/usr/bin/env python3
"""FRONT-END GATE soak: strict 250 ms cadence, scored, for the VERBOSE image.

Same protocol as PROD_CLOSURE.md SS15.4 so the numbers are comparable: the
10 production payloads round-robin, each on the wire EXACTLY ONCE, on a HARD
250.0 ms schedule that does NOT wait for reports (so the firmware's own
blind window shows up as no-report, which is a real production outcome).

Scoring is the SS12.6 double check: an accepted emission must match a known
payload AND the payload temporally attributed to it; a payload matching a
known frame but not the attributed one is counted separately.

    python3 soak_fe.py --minutes 15 [--out F]
"""
import argparse
import glob
import importlib.util
import json
import statistics as S
import sys
import threading
import time
from collections import Counter
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
sys.path.insert(0, str(NEWIMPL / "bench"))
from testprobe import TestProbe                                 # noqa: E402
from crc import build_payload_v23                               # noqa: E402
from epsfmt import parse_eps                                    # noqa: E402
from patterns import HEADER_V23, TRAILER_V23                    # noqa: E402

PIN_POWER, POWER_ON_LEVEL = 28, 1
PIN_UART_RX, PIN_UART_TX, PIN_WS2812 = 1, 0, 29
BAUD = 9600


def prod_frames():
    sp = importlib.util.spec_from_file_location(
        "dp", NEWIMPL / "bench" / "drive_prod.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m.FRAMES


def wire(d):
    fr = HEADER_V23 + build_payload_v23(d) + TRAILER_V23
    assert len(fr) == 60
    return fr


class Reader:
    def __init__(self):
        self.buf = bytearray()
        self.lines = []
        self.banners = 0
        self.lock = threading.Lock()

    def feed(self, data):
        now = time.monotonic()
        with self.lock:
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                ln = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[:nl + 1]
                if ln:
                    t = ln.decode("ascii", "replace")
                    if t.startswith("RBARF-P"):
                        self.banners += 1
                    self.lines.append((now, t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=15.0)
    ap.add_argument("--period", type=float, default=0.250)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(Path(__file__).parent / "soak_fe.json"))
    a = ap.parse_args()
    port = probe_port(a.port)
    FR = prod_frames()
    truth = {n: d.hex().lower() for n, d in FR}
    known = {v: k for k, v in truth.items()}
    rd = Reader()
    sends = []

    with TestProbe(port) as probe:
        print("[probe] %s on %s" % (probe.ident(), port))
        probe.on_uart_rx = rd.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)
        banner = None
        for cyc in range(1, 4):
            print("[bench] power cycle %d/3 (5 s SWIM window)..." % cyc)
            probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
            time.sleep(2.0)
            with rd.lock:
                rd.lines.clear()
            t_on = time.monotonic()
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            for _ in range(150):
                time.sleep(0.1)
                with rd.lock:
                    hit = [x for x in rd.lines if x[1].startswith("RBARF-P")]
                if hit:
                    banner = hit[0]
                    break
            if banner:
                print("[bench] banner %r at %.2f s (SWIM window %s)"
                      % (banner[1], banner[0] - t_on,
                         "OK" if banner[0] - t_on >= 4.5 else "VIOLATED"))
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no banner after 3 power cycles")
        time.sleep(0.3)
        with rd.lock:
            rd.lines.clear()
            b0 = rd.banners
        t0 = time.monotonic() + 0.2
        n = 0
        end = t0 + a.minutes * 60.0
        while True:
            t_due = t0 + n * a.period
            if t_due > end:
                break
            dt = t_due - time.monotonic()
            if dt > 0:
                time.sleep(dt)
            name, data = FR[n % len(FR)]
            ts = time.monotonic()
            probe.ws2812_write(wire(data))
            sends.append({"i": n, "pattern": name, "t": ts - t0})
            n += 1
            if n % 200 == 0:
                with rd.lock:
                    nd = sum(1 for _, l in rd.lines if l.startswith("D:"))
                print("[bench] %d sent, %d D: lines, %.0f s elapsed"
                      % (n, nd, time.monotonic() - t0))
        time.sleep(1.0)
        with rd.lock:
            lines = [(t - t0, l) for t, l in rd.lines]
            resets = rd.banners - b0

    # ---- score -----------------------------------------------------------
    dv = wrong = misattr = refuse = proto = 0
    causes = Counter()
    epss = []
    rows = []
    i = 0
    while i < len(lines):
        t, ln = lines[i]
        if not ln.startswith("D:"):
            i += 1
            continue
        parts = ln.split(":")
        if len(parts) != 3:
            proto += 1
            i += 1
            continue
        st, eps_s = parts[1], parts[2]
        try:
            eps = parse_eps(eps_s)
        except Exception:                                    # noqa: BLE001
            eps = None
        cand = [s for s in sends if t - 0.30 <= s["t"] <= t - 0.14]
        att = cand[-1] if cand else None
        row = {"t": t, "status": st, "eps": eps,
               "attr": att["pattern"] if att else None,
               "attr_i": att["i"] if att else None}
        if st in ("O", "C"):
            ver = None
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j][1].startswith("V:"):
                    ver = lines[j][1][2:].lower()
                    i = j
                    break
            if ver is None:
                proto += 1
            elif att and ver == truth[att["pattern"]]:
                dv += 1
                if eps is not None:
                    epss.append(eps)
            elif ver in known:
                misattr += 1
                row["got"] = known[ver]
            else:
                wrong += 1
                row["got"] = ver
        elif st.startswith("R"):
            refuse += 1
            causes[st] += 1
        else:
            proto += 1
        rows.append(row)
        i += 1

    nrep = len(rows)
    print("=" * 72)
    print("SOAK (verbose image, strict %.0f ms): %d frames sent, %d reports "
          "(%.1f %%)" % (a.period * 1e3, len(sends), nrep,
                         100.0 * nrep / max(len(sends), 1)))
    print("  DELIVERED CORRECT %d (%.1f %% of reports, %.1f %% of frames)"
          % (dv, 100.0 * dv / max(nrep, 1), 100.0 * dv / max(len(sends), 1)))
    print("  refused %d  %s" % (refuse, dict(causes)))
    print("  MISATTRIBUTED %d   **WRONG EMISSIONS %d**   protocol errors %d"
          % (misattr, wrong, proto))
    print("  MCU RESETS %d" % resets)
    if epss:
        # parse_eps() returns CENTI-percent (the wire/report unit)
        print("  eps: n %d  mean %+.3f %%  sd %.3f pp  min %+.2f  max %+.2f  "
              "first %+.2f  last %+.2f  in band [-1.6,-0.4] %d/%d"
              % (len(epss), S.mean(epss) / 100.0, S.pstdev(epss) / 100.0,
                 min(epss) / 100.0, max(epss) / 100.0, epss[0] / 100.0,
                 epss[-1] / 100.0,
                 sum(1 for e in epss if -160 <= e <= -40), len(epss)))
    Path(a.out).write_text(json.dumps(
        {"meta": {"minutes": a.minutes, "period": a.period,
                  "sent": len(sends), "reports": nrep, "delivered": dv,
                  "wrong": wrong, "misattributed": misattr,
                  "refused": refuse, "causes": dict(causes),
                  "resets": resets, "proto": proto},
         "sends": sends, "rows": rows}, indent=1))
    print("[bench] wrote %s" % a.out)


if __name__ == "__main__":
    main()
