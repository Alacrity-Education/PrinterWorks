#!/usr/bin/env python3
"""Candidate per-capture (5,6) boundary estimators, oracle-scored.

For each capture: collect (5,6) L=1 pulses (x = u - psi[5]), marker labels,
cloud; compute candidate thetas BLINDLY; score against truth (eval only).
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


def sharp_fit(intervals, prior, span=130.0):
    """Max-overlap interval-censored point fit (no shrinkage): the h that
    the most label intervals contain; midpoint of the argmax plateau."""
    if not intervals:
        return prior
    events = []
    for lo, hi in intervals:
        events.append((lo, 1))
        events.append((hi, -1))
    events.sort()
    best_n, cur = -1, 0
    seg_lo = seg_hi = prior
    open_lo = None
    for x, dn in events:
        prev = cur
        cur += dn
        if dn > 0 and cur > best_n:
            best_n, open_lo = cur, x
        elif dn < 0 and prev == best_n and open_lo is not None:
            seg_lo, seg_hi = open_lo, x
            open_lo = None
    # fallback midpoint
    if best_n <= 0:
        return prior
    th = (seg_lo + seg_hi) * 0.5
    if abs(th - prior) > span:
        return prior
    return th


results = {}
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    tb = HDR + cm._bits_of(bytes.fromhex(c["payload"])) + TRL
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        continue
    seg = best["seg"]
    model = [m for m in cm.MODELS if m["name"] == best["model"]][0]
    h0p, h1p = model["H0"], model["H1"]
    # forced labels + fits exactly as _try_decode round 1
    forced = []
    for p in seg:
        k0, k1 = p["k0"], p["k1"]
        if k1 > 192 or any(cm.KNOWN[t] < 0 for t in range(k0, k1)):
            continue
        amin, amax = cm._a_bounds(k0, k1)
        if amin == amax:
            forced.append((p, amin))
    h0c, h1c, psi = cm._fit_model(forced, h0p, h1p)

    fam = (5, 6)
    g = sorted(p["v"] - p["u"] for p in seg
               if (p["sfa"], p["sfb"]) == fam)
    if not g:
        continue
    g56 = g[len(g) // 2]
    wa = math.hypot(cm.WE[5], cm.TB_NS)
    wb = math.hypot(cm.WE[6], cm.TB_NS)
    b_probit = cm._probit_boundary(g56, wa, wb, h0c, h1c)

    # marker labels for (5,6) in x-space
    lab0, lab1 = [], []
    for (p, a) in forced:
        li = cm._label_interval(p, a, h0c, h1c)
        if li is None or (p["sfa"], p["sfb"]) != fam:
            continue
        cls, lo, hi = li
        (lab1 if cls else lab0).append(lo - psi[5])
    # sharp global-width fit from ALL families' labels
    i0, i1 = [], []
    for (p, a) in forced:
        li = cm._label_interval(p, a, h0c, h1c)
        if li is None:
            continue
        cls, lo, hi = li
        iv = (lo - psi[p["sfa"]], hi - psi[p["sfb"]])
        (i1 if cls else i0).append(iv)
    h0s = sharp_fit(i0, h0c)
    h1s = sharp_fit(i1, h1c)

    # cloud: (5,6) pulses folded, x-space
    cloud = []
    for p in seg:
        if (p["sfa"], p["sfb"]) != fam:
            continue
        up = p["u"] - psi[5]
        x = up - 1250.0 * round((up - b_probit) / 1250.0)
        cloud.append(x)
    cloud.sort()

    # oracle: PAYLOAD-only L=1 truth (marker pulses are forced anyway)
    xs = []
    for p in seg:
        if (p["sfa"], p["sfb"]) != fam or p["k1"] - p["k0"] != 1 \
                or not (32 <= p["k0"] < 160):
            continue
        xs.append((p["u"] - psi[5], tb[p["k0"]], p["k0"]))
    if not xs:
        continue
    results[name] = dict(b=b_probit, h0c=h0c, h1c=h1c, h0s=h0s, h1s=h1s,
                         g=g56, lab0=sorted(lab0), lab1=sorted(lab1),
                         cloud=cloud, xs=xs, ok=best["payload"] ==
                         bytes.fromhex(c["payload"]))


def score(theta_of):
    tot = 0
    bad = []
    for name, r in results.items():
        th = theta_of(r)
        e = sum(1 for x, cls, k in r["xs"] if (0 if x <= th else 1) != cls)
        tot += e
        if e:
            bad.append((name, e, round(th, 1)))
    return tot, bad


def est_probit(r):
    return r["b"]


def est_sharp(r):
    return (r["h0s"] + r["h1s"] - r["g"]) * 0.5


def est_sharp_clip(r):
    th = est_sharp(r)
    lo = max(r["lab0"]) + 2.0 if r["lab0"] else None
    hi = min(r["lab1"]) - 2.0 if r["lab1"] else None
    if lo is not None and hi is not None and lo > hi:
        return (max(r["lab0"]) + min(r["lab1"])) * 0.5
    if lo is not None:
        th = max(th, lo)
    if hi is not None:
        th = min(th, hi)
    return th


def est_lab_mid(r):
    if r["lab0"] and r["lab1"]:
        return (max(r["lab0"]) + min(r["lab1"])) * 0.5
    return r["b"]


def gap_split(r, zone_lo, zone_hi, fallback):
    pts = [x for x in r["cloud"] if zone_lo < x < zone_hi]
    if not pts:
        return (zone_lo + zone_hi) * 0.5
    seqs = [zone_lo] + pts + [zone_hi]
    gz = [seqs[i + 1] - seqs[i] for i in range(len(seqs) - 1)]
    bi = max(range(len(gz)), key=lambda i: gz[i])
    if gz[bi] < 12.0:
        return fallback
    if len(gz) >= 4:
        srt = sorted(gz)
        if gz[bi] < 2.5 * srt[len(srt) // 2]:
            return fallback
    return (seqs[bi] + seqs[bi + 1]) * 0.5


def est_current(r):
    lo = max(r["lab0"]) if r["lab0"] else r["b"] - 80.0
    hi = min(r["lab1"]) if r["lab1"] else r["b"] + 80.0
    lo = max(lo, r["b"] - 80.0)
    hi = min(hi, r["b"] + 80.0)
    if lo >= hi:
        return r["b"]
    return gap_split(r, lo, hi, r["b"])


def est_gap_sharpfb(r):
    """largest-gap split in the label zone, falling back to sharp-h."""
    fb = est_sharp_clip(r)
    lo = max(r["lab0"]) if r["lab0"] else fb - 60.0
    hi = min(r["lab1"]) if r["lab1"] else fb + 60.0
    if lo >= hi:
        return fb
    th = gap_split(r, lo, hi, fb)
    return th


def make_preg(sig, prior_w, prior_of, zone=80.0, rep_w=0.0, rep_sig=12.0,
              span=60.0):
    def est(r):
        b0 = prior_of(r)
        pts0 = [x for x in r["lab0"] if x > b0 - zone]
        pts1 = [x for x in r["lab1"] if x < b0 + zone]
        cloud = [x for x in r["cloud"] if abs(x - b0) < zone] \
            if rep_w else []

        def cost(th):
            c = prior_w * ((th - b0) / sig) ** 2
            for x in pts0:
                c += -cm._log_ndtr((th - x) / sig)
            for x in pts1:
                c += -cm._log_ndtr((x - th) / sig)
            for x in cloud:
                c += -rep_w * cm._log_ndtr(abs(x - th) / rep_sig)
            return c
        best_t, best_c = b0, None
        t = b0 - span
        while t <= b0 + span:
            cc = cost(t)
            if best_c is None or cc < best_c:
                best_c, best_t = cc, t
            t += 1.0
        return best_t
    return est


for tag, fn in (("probit b (no eps)", est_probit),
                ("sharp (h0s+h1s-g)/2", est_sharp),
                ("sharp clipped to labels", est_sharp_clip),
                ("label midpoint (b fb)", est_lab_mid),
                ("current gap+guard (b fb)", est_current),
                ("gap, sharp-clip fallback", est_gap_sharpfb),
                ("preg sig=40 w=1 b", make_preg(40.0, 1.0, est_probit)),
                ("preg40 rep .5/12", make_preg(40.0, 1.0, est_probit,
                                               rep_w=0.5, rep_sig=12.0)),
                ("preg40 rep 1/12", make_preg(40.0, 1.0, est_probit,
                                              rep_w=1.0, rep_sig=12.0)),
                ("preg40 rep .5/8", make_preg(40.0, 1.0, est_probit,
                                              rep_w=0.5, rep_sig=8.0)),
                ("preg40 rep .25/16", make_preg(40.0, 1.0, est_probit,
                                                rep_w=0.25, rep_sig=16.0)),
                ("preg50 w=1 b", make_preg(50.0, 1.0, est_probit)),
                ("preg45 w=1 b", make_preg(45.0, 1.0, est_probit)),
                ("preg35 w=1 b", make_preg(35.0, 1.0, est_probit)),
                ("preg40 w=.5 b", make_preg(40.0, 0.5, est_probit)),
                ("preg40 w=2 b", make_preg(40.0, 2.0, est_probit))):
    tot, bad = score(fn)
    print(f"{tag:28s} errors={tot:3d}  bad={bad}")

# per-capture detail for currently failing captures
FAIL = ["p55_0", "blocks_0", "nibbles_1", "sparse_1", "runs_2", "rnd2_0",
        "zeros_0", "edges_2", "rnd2_1", "rnd3_2", "sparse_0", "blocks_1",
        "blocks_2", "p55_1"]
print("\nper-capture detail:")
for name in FAIL:
    if name not in results:
        continue
    r = results[name]
    x0 = sorted(x for x, cls, k in r["xs"] if cls == 0)
    x1 = sorted(x for x, cls, k in r["xs"] if cls == 1)
    print(f"\n{name}: b={r['b']:.1f} h0c={r['h0c']:.1f} h1c={r['h1c']:.1f} "
          f"h0s={r['h0s']:.1f} h1s={r['h1s']:.1f} g={r['g']:.1f} "
          f"sharp_th={est_sharp(r):.1f}")
    print(f"  lab0={[round(x,1) for x in r['lab0']]}")
    print(f"  lab1={[round(x,1) for x in r['lab1']]}")
    print(f"  oracle max0={max(x0) if x0 else None} "
          f"min1={min(x1) if x1 else None}")
    zl = max(r["lab0"]) if r["lab0"] else r["b"] - 80
    zh = min(r["lab1"]) if r["lab1"] else r["b"] + 80
    print(f"  cloud in zone ({zl:.1f},{zh:.1f}): "
          f"{[round(x,1) for x in r['cloud'] if zl < x < zh]}")
