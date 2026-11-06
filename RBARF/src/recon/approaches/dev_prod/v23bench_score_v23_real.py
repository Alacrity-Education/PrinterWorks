#!/usr/bin/env python3
"""Score the FRESH real-silicon v2.3 corpora with the Python reference
decoder at the SHIPPED v2.3 constants.  No parameter overrides."""
import importlib.util, json, sys
from collections import Counter
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NEWIMPL / "recon"))
from harness import linearize  # noqa

spec = importlib.util.spec_from_file_location(
    "embedded_v2_s", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)

ND = 16
ev._configure(ND, chk=6)

rows = []
for f in ("captures_v23.json", "captures_v23_val.json"):
    d = json.loads((NEWIMPL / "data" / f).read_text())
    caps = d["captures"]
    deliv = wrong = ref = 0
    causes = Counter(); paths = Counter(); per_pat = {}
    for c in caps:
        truth = bytes.fromhex(c["payload"])[:ND]
        out, info = ev.decode_ex(linearize(c["capture"]))
        pat = c["pattern"]
        st = per_pat.setdefault(pat, [0, 0, 0])
        if out is None:
            ref += 1; causes[info["cause"]] += 1; st[2] += 1
        elif out == truth:
            deliv += 1; paths[info["path"]] += 1; st[0] += 1
        else:
            wrong += 1; paths[info["path"]] += 1; st[1] += 1
            rows.append(dict(file=f, pattern=pat, rep=c["rep"],
                             truth=truth.hex().upper(),
                             emitted=out.hex().upper(),
                             path=info["path"], trials=info.get("trials"),
                             comps=info.get("comps"),
                             n_refs=info.get("n_refs"),
                             K=info.get("K"), tau=info.get("tau"),
                             violations=info.get("violations")))
    n = len(caps)
    print("=== %s : %d captures ===" % (f, n))
    print("  delivered %d (%.2f%%)   refused %d (%.2f%%)   WRONG %d (%.2f%%)"
          % (deliv, 100.0*deliv/n, ref, 100.0*ref/n, wrong, 100.0*wrong/n))
    if deliv + wrong:
        print("  wrong-emission rate: %d/%d = %.4f%% of emissions"
              % (wrong, deliv+wrong, 100.0*wrong/(deliv+wrong)))
    print("  paths   :", dict(paths))
    print("  refusals:", dict(causes) or "none")
    bad = {k: v for k, v in per_pat.items() if v[1] or v[2]}
    if bad:
        print("  patterns with refusals/wrong (ok,wrong,ref):", bad)
    print()

if rows:
    print("WRONG EMISSIONS (detail):")
    for r in rows:
        print("  ", r)
else:
    print("WRONG EMISSIONS: none")
