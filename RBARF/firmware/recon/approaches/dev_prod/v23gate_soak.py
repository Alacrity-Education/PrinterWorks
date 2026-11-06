#!/usr/bin/env python3
"""v2.3 SOAK + WARM 30-frame GATE, one bench session (one power cycle).

Flashed image must be ``build/rbarf_prod_verbose.ihx`` (VERBOSE=1: the
``V:`` line is what makes a wrong emission observable at all).

Phase 1  SOAK   -- the 10 production frames cycled at a STRICT spacing
                   (default 250 ms, the production cadence), for
                   ``--secs`` seconds.  Every ``D:``/``V:`` pair is
                   scored two independent ways, exactly as PROD_CLOSURE
                   SS12.6 did: the emitted payload must (a) match one of
                   the 10 known frames and (b) match the frame that was
                   most recently ON THE WIRE when the report arrived
                   (temporal attribution).  A payload that matches a
                   known frame but not the attributed one is counted
                   separately as UNATTRIBUTABLE -- it is not scored as
                   correct.
Phase 2  GATE    -- 30 frames (10 x 3) with drive_prod.py's protocol
                   verbatim, WARM, no power cycle in between.

Wrong emissions (payload not equal to the attributed frame and not any
known frame) are the headline number and must be 0.
"""
import argparse
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
sys.path.insert(0, str(NEWIMPL / "bench"))
from testprobe import TestProbe                                # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "drive_prod_mod", NEWIMPL / "bench" / "drive_prod.py")
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)                                    # noqa: E402

FRAMES = dp.FRAMES
BY_HEX = {d.hex().lower(): n for n, d in FRAMES}


def wait_banner(probe, reader):
    for cycle in range(1, 4):
        print(f"[bench] power cycle {cycle}/3 (5 s SWIM window)...")
        probe.gpio_write(dp.PIN_POWER, 1 - dp.POWER_ON_LEVEL)
        time.sleep(2.0)
        reader.drop_all()
        t_on = time.monotonic()
        probe.gpio_write(dp.PIN_POWER, dp.POWER_ON_LEVEL)
        ts, td, banner = reader.wait_for("RBARF-P", 15.0)
        if banner is not None:
            dt = ts - t_on
            print(f"[bench] banner {banner!r} at {dt:.2f} s "
                  f"(SWIM quiet window {'OK' if dt >= 4.5 else 'VIOLATED'})")
            return dt
    raise SystemExit("[bench] FAIL: no banner after 3 power cycles -- STOP")


def soak(probe, reader, secs, spacing_ms):
    """Strict-cadence soak.  Returns a result dict."""
    spacing = spacing_ms / 1000.0
    sent_log = []                 # (t_sent, name, hex)
    reader.drop_all()
    with reader.cond:
        b0 = reader.banners
    t_start = time.monotonic()
    k = 0
    reports = []
    n_sent = 0
    while True:
        now = time.monotonic()
        if now - t_start >= secs:
            break
        name, data = FRAMES[k % len(FRAMES)]
        k += 1
        fr = dp.frame(data)
        t_send = time.monotonic()
        probe.ws2812_write(fr)
        n_sent += 1
        sent_log.append((t_send, name, data.hex().lower()))
        # drain whatever complete lines have arrived, without blocking
        with reader.cond:
            got = list(reader.lines)
            reader.lines.clear()
        reports.extend(got)
        nxt = t_start + n_sent * spacing
        dt = nxt - time.monotonic()
        if dt > 0:
            time.sleep(dt)
    time.sleep(1.5)
    with reader.cond:
        reports.extend(list(reader.lines))
        reader.lines.clear()
        b1 = reader.banners
    soak_secs = time.monotonic() - t_start

    # ---- pair D: with the V: that follows it, then attribute ----------
    n_d = n_v = 0
    delivered = wrong = unattrib = refused = 0
    causes = {}
    epss = []
    eps_series = []
    pending = None                       # (t_done, status, eps)
    wrong_rows = []
    for ts, td, line in reports:
        if line.startswith("D:"):
            n_d += 1
            try:
                _, st, eps_s = line.split(":")
                eps = dp.parse_eps(eps_s)
            except ValueError:
                continue
            if st in ("O", "C"):
                pending = (td, st, eps)
            else:
                refused += 1
                causes[dp.CAUSE.get(st[1:2], st)] = \
                    causes.get(dp.CAUSE.get(st[1:2], st), 0) + 1
                pending = None
        elif line.startswith("V:") and pending is not None:
            n_v += 1
            td_d, st, eps = pending
            pending = None
            got = line[2:].lower()
            # temporal attribution: newest frame sent strictly before the
            # report finished (the decode cannot precede its own capture)
            attrib = None
            for t_s, nm, hx in reversed(sent_log):
                if t_s < td_d:
                    attrib = (nm, hx)
                    break
            if attrib is not None and got == attrib[1]:
                delivered += 1
                epss.append(eps)
                eps_series.append((td_d, eps))
            elif got in BY_HEX:
                unattrib += 1
                epss.append(eps)
                eps_series.append((td_d, eps))
            else:
                wrong += 1
                wrong_rows.append(dict(status=st, eps_centi=eps,
                                       emitted=got,
                                       attributed=attrib[1] if attrib else None,
                                       attributed_name=attrib[0] if attrib else None))
    return dict(secs=soak_secs, spacing_ms=spacing_ms, sent=n_sent,
                reports=n_d, v_lines=n_v, delivered=delivered,
                unattributable=unattrib, wrong=wrong, refused=refused,
                causes=causes, resets=b1 - b0, epss=epss,
                eps_series=eps_series, wrong_rows=wrong_rows)


def gate(probe, reader, reps, label):
    """drive_prod.py's 30-frame protocol, verbatim, in this session."""
    rows = []
    n_ok = n_chase = n_refuse = n_cat = n_proto = n_noreport = 0
    with reader.cond:
        b_seen = reader.banners
    n_reset = 0
    total = len(FRAMES) * reps
    done = 0
    for rep in range(reps):
        for name, data in FRAMES:
            fr = dp.frame(data)
            time.sleep(0.25)
            reader.drop_all()
            t0 = time.monotonic()
            probe.ws2812_write(fr)
            ts_d, td_d, dec = reader.wait_for("D:", 1.5)
            done += 1
            row = {"pattern": name, "rep": rep, "sent": data.hex()}
            with reader.cond:
                b_now = reader.banners
            reset_here = b_now > b_seen
            if reset_here:
                n_reset += b_now - b_seen
                b_seen = b_now
            if dec is None:
                n_noreport += 1
                row.update(verdict="MISSED", status="NO-REPORT",
                           reset_seen=reset_here)
                rows.append(row)
                print(f"[{label}] {done:3d}/{total} {name:13s} r{rep}: "
                      f"MISSED       (no report"
                      f"{', MCU RESET' if reset_here else ''})")
                continue
            try:
                _, status, eps_s = dec.split(":")
                eps = dp.parse_eps(eps_s)
            except ValueError:
                n_proto += 1
                row.update(verdict="PROTOCOL-ERROR", line=dec)
                rows.append(row)
                print(f"[{label}] {done:3d}/{total} BAD LINE {dec[:50]!r}")
                continue
            got = None
            if status in ("O", "C"):
                ts_v, td_v, ver = reader.wait_for("V:", 3.0)
                if ver is None:
                    n_proto += 1
                    row.update(verdict="PROTOCOL-ERROR",
                               note="no V: after verified decode")
                    rows.append(row)
                    print(f"[{label}] {done:3d}/{total} PROTOCOL-ERROR "
                          f"(no V:)")
                    continue
                got = ver[2:]
                if got.lower() == data.hex().lower():
                    verdict = "DELIVERED"
                    if status == "O":
                        n_ok += 1
                    else:
                        n_chase += 1
                else:
                    verdict = "CATASTROPHIC"
                    n_cat += 1
            elif status.startswith("R") and len(status) == 2:
                verdict = "MISSED"
                n_refuse += 1
            else:
                verdict = "PROTOCOL-ERROR"
                n_proto += 1
            transit_ms = (len(dec) + 2) * dp.CHAR_MS
            lat_ms = (td_d - t0) * 1e3
            decode_ms = lat_ms - dp.FRAME_TX_MS - dp.CAPTURE_MS - transit_ms
            row.update(verdict=verdict, status=status, eps_centi=eps,
                       got=got, line=dec, latency_ms=lat_ms,
                       decode_ms=decode_ms)
            rows.append(row)
            cz = ("R" + dp.CAUSE.get(status[1], "?")) \
                if verdict == "MISSED" and status.startswith("R") else status
            print(f"[{label}] {done:3d}/{total} {name:13s} r{rep}: "
                  f"{verdict:12s} {cz:11s} eps {eps/100.0:+.2f}%  "
                  f"decode ~{decode_ms:.1f} ms")
    return dict(rows=rows, total=total, ok=n_ok, chase=n_chase,
                refused=n_refuse, catastrophic=n_cat, proto=n_proto,
                noreport=n_noreport, resets=n_reset)


def summarise_gate(g, label):
    d = g["ok"] + g["chase"]
    causes = {}
    for r in g["rows"]:
        st = r.get("status", "")
        if r.get("verdict") == "MISSED" and st.startswith("R") and len(st) == 2:
            c = dp.CAUSE.get(st[1], st)
            causes[c] = causes.get(c, 0) + 1
    epss = [r["eps_centi"] for r in g["rows"]
            if r.get("verdict") == "DELIVERED"]
    print()
    print("=" * 72)
    print(f"{label}: {d}/{g['total']} delivered correct "
          f"({g['ok']} O + {g['chase']} C), {g['refused']} refused, "
          f"{g['noreport']} no-report, {g['catastrophic']} CATASTROPHIC, "
          f"{g['proto']} protocol errors, {g['resets']} resets")
    print(f"  refusal causes: {causes}")
    if epss:
        print(f"  eps on delivered: min {min(epss)/100:+.2f}% "
              f"max {max(epss)/100:+.2f}% mean {sum(epss)/len(epss)/100:+.3f}%"
              f"  in-band[-1.6,-0.4] {sum(1 for e in epss if -160 <= e <= -40)}"
              f"/{len(epss)}")
    print("=" * 72)
    g["causes"] = causes
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secs", type=float, default=900.0)
    ap.add_argument("--spacing-ms", type=float, default=250.0)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        NEWIMPL / "recon" / "approaches" / "dev_prod" /
        "bench_v23_soak_warm.json"))
    a = ap.parse_args()
    import glob
    port = probe_port(a.port)
    reader = dp.LineReader()
    with TestProbe(port) as probe:
        print(f"[probe] {probe.ident()} on {port}")
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(dp.PIN_WS2812)
        probe.uart_config(dp.PIN_UART_TX, dp.PIN_UART_RX, dp.BAUD)
        banner_s = wait_banner(probe, reader)
        time.sleep(0.3)
        print(f"[soak] {a.secs:.0f} s at a strict {a.spacing_ms:.0f} ms "
              f"cadence...")
        s = soak(probe, reader, a.secs, a.spacing_ms)
        print()
        print("=" * 72)
        print(f"SOAK {s['secs']:.1f} s @ {s['spacing_ms']:.0f} ms: "
              f"{s['sent']} sent, {s['reports']} reports, "
              f"{s['delivered']} delivered CORRECT, "
              f"{s['unattributable']} unattributable, "
              f"{s['wrong']} WRONG, {s['refused']} refused, "
              f"{s['resets']} RESETS")
        print(f"  refusal causes: {s['causes']}")
        if s["epss"]:
            e = s["epss"]
            print(f"  eps: n {len(e)} min {min(e)/100:+.2f}% "
                  f"max {max(e)/100:+.2f}% mean {sum(e)/len(e)/100:+.3f}% "
                  f"sd {statistics.pstdev(e)/100:.3f} pp  "
                  f"in-band {sum(1 for x in e if -160 <= x <= -40)}/{len(e)}")
            q = len(e) // 4
            if q:
                print(f"  eps drift: first quarter mean "
                      f"{sum(e[:q])/q/100:+.3f}%  last quarter mean "
                      f"{sum(e[-q:])/q/100:+.3f}%")
        print("=" * 72)
        print()
        g = gate(probe, reader, a.reps, "warm")
        dcount = summarise_gate(g, "WARM GATE (post-soak)")
    s.pop("eps_series", None)
    out = Path(a.out)
    out.write_text(json.dumps({
        "meta": {"firmware": "rbarf_prod_verbose.ihx (v2.3, TRAILER 9A00FF, "
                             "hex-eps VERBOSE report)",
                 "banner_s": banner_s,
                 "scoring": "soak: D:+V: paired, payload must match a known "
                            "frame AND its temporal attribution; "
                            "gate: drive_prod.py protocol verbatim"},
        "soak": s, "warm_gate": g}, indent=1))
    print(f"[bench] wrote {out}")


if __name__ == "__main__":
    main()
