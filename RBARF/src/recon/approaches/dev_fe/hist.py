#!/usr/bin/env python3
"""Pooled refusal-cause histogram + totals over this phase's production runs."""
import json
import sys
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parent
CAUSE = {"1": "R1", "2": "R2", "3": "R3", "4": "R4", "5": "R5", "6": "R6",
         "7": "R7", "8": "R8"}


def gate(p):
    d = json.loads(Path(p).read_text())
    c = Counter()
    sent = dv = wrong = nore = 0
    for r in d["rows"]:
        sent += 1
        v = r.get("verdict")
        if v == "DELIVERED":
            dv += 1
        elif v == "CATASTROPHIC":
            wrong += 1
        st = str(r.get("status") or "")
        if st.startswith("REFUSE"):            # test_klipper_macro.py form
            st = "R" + st[6:]
        if st.startswith("R") and len(st) == 2 and st[1].isdigit():
            c[st] += 1
        elif st == "NO-REPORT":
            nore += 1
    return sent, dv, wrong, nore, c, d["meta"].get("resets", 0)


def main():
    tot = Counter()
    sent = dv = wrong = nore = resets = 0
    for tag, p in (("cold", D / "gate_cold.json"),
                   ("warm", D / "gate_warm.json"),
                   ("klipper", D / "klipper_fe.json")):
        if not p.exists():
            print("MISSING", p)
            continue
        s, d_, w, nr, c, rs = gate(p)
        print("%-8s sent %3d delivered %3d wrong %d no-report %d %s resets %s"
              % (tag, s, d_, w, nr, dict(c), rs))
        tot += c
        sent += s
        dv += d_
        wrong += w
        nore += nr
        resets += rs if isinstance(rs, int) else 0
    sp = D / "soak_warm.json"
    if sp.exists():
        m = json.loads(sp.read_text())["meta"]
        print("soak     sent %4d reports %4d delivered %4d wrong %d "
              "misattr %d refused %d resets %d"
              % (m["sent"], m["reports"], m["delivered"], m["wrong"],
                 m["misattributed"], m["refused"], m["resets"]))
        for k, v in m["causes"].items():
            tot[k] += v
        sent += m["sent"]
        dv += m["delivered"]
        wrong += m["wrong"]
        resets += m["resets"]
    n = sum(tot.values())
    print("\nPOOLED: %d frames on the wire, %d accepted emissions, %d WRONG, "
          "%d MCU resets" % (sent, dv, wrong, resets))
    print("REFUSALS %d:" % n)
    for k in ("R3", "R1", "R6", "R8", "R4", "R2", "R7", "R5"):
        if tot.get(k):
            print("   %-3s %4d  %5.1f %%" % (k, tot[k], 100.0 * tot[k] / n))
    fe = tot.get("R1", 0) + tot.get("R2", 0) + tot.get("R3", 0) + \
        tot.get("R4", 0)
    print("   front end (R1+R2+R3+R4) %d = %.1f %% of refusals"
          % (fe, 100.0 * fe / n if n else 0.0))
    print("   R1+R3 only %d = %.1f %%"
          % (tot.get("R1", 0) + tot.get("R3", 0),
             100.0 * (tot.get("R1", 0) + tot.get("R3", 0)) / n if n else 0.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
