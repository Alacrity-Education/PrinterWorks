#!/usr/bin/env python3
"""Sensitivity / ablation probes (monkeypatched; combined.py untouched)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "approaches"))
from harness import load_dataset, linearize  # noqa: E402
import importlib.util  # noqa: E402


def fresh():
    spec = importlib.util.spec_from_file_location(
        "combined", ROOT / "approaches" / "combined.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


meta, caps = load_dataset()
DATA = [(f"{c['pattern']}_{c['rep']}", c["rep"], linearize(c["capture"]),
         bytes.fromhex(c["payload"])) for c in caps]


def run(m, tag):
    ok = tr = ho = 0
    miss = []
    for name, rep, s, exp in DATA:
        try:
            d = m.decode(s, meta)
        except Exception as e:
            d = None
            print("  raised", name, repr(e))
        good = (d == exp)
        ok += good
        if rep == 2:
            ho += good
        else:
            tr += good
        if not good:
            miss.append(name)
    print(f"{tag:34s} all={ok}/54 train={tr}/36 holdout={ho}/18")
    print(f"    misses: {miss}")
    return ok


m = fresh()
run(m, "baseline (as shipped)")

m = fresh()
m.DEAD_PRIOR_NATS = 0.0
run(m, "DEAD_PRIOR_NATS = 0.0")

m = fresh()
m.DEAD_PRIOR_NATS = -0.45
run(m, "DEAD_PRIOR_NATS = -0.45 (more-ones)")

m = fresh()
m.MODELS = (m.MODELS[0],)
run(m, "only 'cal' model")

m = fresh()
m.MODELS = (m.MODELS[1],)
run(m, "only 'fit' model (fitted_model.json)")

m = fresh()
m.TIE_NATS = 0.0
run(m, "TIE_NATS = 0.0")

m = fresh()
m.N_ALIAS = 1
run(m, "N_ALIAS = 1 (no alias retry)")


# disable the sweep-dominance guard inside _fit_family_eps
def no_guard(m):
    import math
    orig = m._fit_family_eps

    def patched(seg, labelled, h0c, h1c, psi):
        # copy of the original with the sweep-dominance test removed
        fam_x, fam_gap = {}, {}
        for p in seg:
            fam_gap.setdefault((p["sfa"], p["sfb"]), []).append(
                p["v"] - p["u"])
        bnd = {}
        for fam, gaps in fam_gap.items():
            g = sorted(gaps)[len(gaps) // 2]
            wa = math.hypot(m.WE[fam[0]], m.TB_NS)
            wb = math.hypot(m.WE[fam[1]], m.TB_NS)
            bnd[fam] = m._probit_boundary(g, wa, wb, h0c, h1c)
        for p in seg:
            fam = (p["sfa"], p["sfb"])
            up = p["u"] - psi[fam[0]]
            x = up - m.BIT * round((up - bnd[fam]) / m.BIT)
            fam_x.setdefault(fam, []).append(x)
        lab_x = {}
        for (p, a) in labelled:
            li = m._label_interval(p, a, h0c, h1c)
            if li is None:
                continue
            cls, lo, hi = li
            fam = (p["sfa"], p["sfb"])
            lab_x.setdefault(fam, []).append((lo - psi[fam[0]], cls))
        eps = {}
        for fam, labs in lab_x.items():
            x0 = [x for x, c in labs if c == 0]
            x1 = [x for x, c in labs if c == 1]
            b = bnd[fam]
            zone_lo = max(x0) if x0 else b - m.ZONE_HALF
            zone_hi = min(x1) if x1 else b + m.ZONE_HALF
            zone_lo = max(zone_lo, b - m.ZONE_HALF)
            zone_hi = min(zone_hi, b + m.ZONE_HALF)
            if x0 and x1 and (min(x1) - max(x0)) < m.SEP_MIN:
                continue
            if zone_lo >= zone_hi:
                continue
            pts = sorted(x for x in fam_x.get(fam, ())
                         if zone_lo < x < zone_hi)
            if not pts:
                if not (x0 and x1):
                    continue
                theta = (zone_lo + zone_hi) * 0.5
            else:
                seqs = [zone_lo] + pts + [zone_hi]
                gz = [seqs[i + 1] - seqs[i] for i in range(len(seqs) - 1)]
                bi = max(range(len(gz)), key=lambda i: gz[i])
                theta = (seqs[bi] + seqs[bi + 1]) * 0.5
            e = theta - b
            eps[fam] = max(-m.EPS_CLAMP, min(m.EPS_CLAMP, e))
        return eps
    m._fit_family_eps = patched
    return orig


m = fresh()
no_guard(m)
run(m, "sweep-dominance guard REMOVED")
