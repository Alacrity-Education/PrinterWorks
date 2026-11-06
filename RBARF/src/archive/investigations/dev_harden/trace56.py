#!/usr/bin/env python3
"""Trace the (5,6) boundary decision inside the real pipeline, per fit round.

Prints, for each target capture: b, pts0/pts1 (in-zone labels), cloud points
near the zone, which branch decided theta, the resulting eps, and the truth
of every payload L=1 (5,6) pulse (x-space) so the required boundary window
is visible next to the chosen one.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "combined", ROOT / "approaches" / "combined.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

meta, caps = load_dataset()
HDR = cm._bits_of(cm.HDR)
TRL = cm._bits_of(cm.TRL)

TARGETS = sys.argv[1:] or [
    "p55_0", "blocks_0", "nibbles_1", "sparse_0", "sparse_1", "runs_2",
    "edges_2", "rnd2_0", "zeros_0", "impulse_lo_2"]

TRACE = []
_orig_ffe = cm._fit_family_eps


def spy_ffe(seg, labelled, h0c, h1c, psi):
    fam = (5, 6)
    # replicate the internals for the trace
    gaps = [p["v"] - p["u"] for p in seg if (p["sfa"], p["sfb"]) == fam]
    rec = dict(n_lab=len(labelled), h0c=h0c, h1c=h1c,
               psi5=psi[5], psi6=psi[6])
    if gaps:
        g = sorted(gaps)[len(gaps) // 2]
        wa = math.hypot(cm.WE[5], cm.TB_NS)
        wb = math.hypot(cm.WE[6], cm.TB_NS)
        b = cm._probit_boundary(g, wa, wb, h0c, h1c)
        cloud = []
        for p in seg:
            if (p["sfa"], p["sfb"]) != fam:
                continue
            up = p["u"] - psi[5]
            x = up - cm.BIT * round((up - b) / cm.BIT)
            cloud.append((x, p["k0"]))
        x0, x1 = [], []
        for (p, a) in labelled:
            li = cm._label_interval(p, a, h0c, h1c)
            if li is None or (p["sfa"], p["sfb"]) != fam:
                continue
            cls, lo, hi = li
            (x1 if cls else x0).append(lo - psi[5])
        rec.update(b=b, cloud=sorted(cloud),
                   x0=sorted(x0), x1=sorted(x1),
                   pts0=[x for x in x0 if abs(x - b) < cm.PREG_ZONE],
                   pts1=[x for x in x1 if abs(x - b) < cm.PREG_ZONE],
                   clear1=[x for x, k in cloud if x > b + cm.PREG_CLEAR1],
                   top=[x for x, k in cloud
                        if b - cm.EPS_CLAMP < x <= b + cm.PREG_CLEAR1])
    eps = _orig_ffe(seg, labelled, h0c, h1c, psi)
    rec["eps56"] = eps.get(fam)
    rec["all_eps"] = {k: round(v, 1) for k, v in eps.items()}
    TRACE.append(rec)
    return eps


cm._fit_family_eps = spy_ffe

BY = {f"{c['pattern']}_{c['rep']}": c for c in caps}
for name in TARGETS:
    c = BY[name]
    samples = linearize(c["capture"])
    tb = HDR + cm._bits_of(bytes.fromhex(c["payload"])) + TRL
    TRACE.clear()
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        print(f"\n### {name}: REFUSED")
        continue
    ok = best["payload"] == bytes.fromhex(c["payload"])
    print(f"\n### {name}  {'OK' if ok else 'MISS'}  model={best['model']} "
          f"rounds_traced={len(TRACE)}")
    # payload truth for L=1 (5,6) pulses under the final fit
    fin = TRACE[-1] if TRACE else None
    for i, r in enumerate(TRACE):
        if "b" not in r:
            continue
        print(f"  round{i}: nlab={r['n_lab']} h0c={r['h0c']:.1f} "
              f"h1c={r['h1c']:.1f} psi5={r['psi5']:.1f} psi6={r['psi6']:.1f} "
              f"b={r['b']:.1f} eps56="
              f"{'None' if r['eps56'] is None else format(r['eps56'], '.1f')}")
        print(f"    pts0(in-zone)={[round(x, 1) for x in r['pts0'][-4:]]}"
              f" pts1={[round(x, 1) for x in r['pts1'][:4]]}")
        zl, zh = r["b"] - 70, r["b"] + 70
        print(f"    cloud near zone: "
              f"{[(round(x, 1), k) for x, k in r['cloud'] if zl < x < zh]}")
        print(f"    clear1(> b+{cm.PREG_CLEAR1:.0f})="
              f"{[round(x, 1) for x in r['clear1']]}  "
              f"top_max={max(r['top']) if r['top'] else None}")
    if fin and "b" in fin:
        th = fin["b"] + (fin["eps56"] or 0.0)
        rows = []
        for p in best["seg"]:
            if (p["sfa"], p["sfb"]) != (5, 6):
                continue
            if p["k1"] - p["k0"] != 1 or not (32 <= p["k0"] < 160):
                continue
            x = p["u"] - fin["psi5"]
            x -= cm.BIT * round((x - fin["b"]) / cm.BIT)
            rows.append((x, p["k0"], tb[p["k0"]], p["a_hat"],
                         best["llr"][p["k0"]]))
        rows.sort()
        print(f"    FINAL theta={th:.1f}; payload L=1 pulses (x, bit, truth,"
              f" a_hat, llr):")
        for x, k, t, a, llr in rows:
            mark = "" if (a > 0) == (t == 1) else "   <-- WRONG"
            print(f"      x={x:7.1f} bit{k:3d} truth={t} a_hat={a} "
                  f"llr={llr:+.3f}{mark}")
