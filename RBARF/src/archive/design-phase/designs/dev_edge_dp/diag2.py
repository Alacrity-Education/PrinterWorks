"""Test the data-dependent time-base hypothesis.

H1: each *high* sample read costs delta_h extra ns (branch on pin level),
    so cumulative time = base(i,s) + delta_h * (#high samples before).
Also try: extra cost per *level change* (edge), and per high *loop*.
"""
import json
import model as M
from fit_slots import FRAME_NS

fit = json.load(open("slotfit.json"))
O = fit["o"]
meta, D = M.load()


def cum_feature(obs, mode):
    """running count feature evaluated BEFORE each sample."""
    out = []
    c = 0
    prev = obs[0]
    for v in obs:
        out.append(c)
        if mode == "high":
            c += v
        elif mode == "edge":
            c += (v != prev)
        prev = v
    return out


def score(bits, idx, obs, feat, o, k, phi, alpha):
    ok = n = 0
    for (i, s), v, f in zip(idx, obs, feat):
        t = phi + k * (i * M.L_NOM + o[s] + alpha * f)
        if not (-200 <= t < FRAME_NS + 200):
            continue
        n += 1
        ok += (M.level_at(bits, t) == v)
    return ok, n


def fit_cap(bits, idx, obs, feat, o, alpha):
    best = (-1, 0.0, 1.0)
    for k in [1.0 + 0.0006 * j for j in range(-18, 31)]:
        for phi in [x * 15.0 for x in range(-34, 35)]:
            ok, _ = score(bits, idx, obs, feat, o, k, phi, alpha)
            if ok > best[0]:
                best = (ok, phi, k)
    for sp, sk in ((6.0, 2e-4), (2.0, 6e-5), (0.5, 2e-5)):
        imp = True
        while imp:
            imp = False
            _, phi, k = best
            for dp in (-2, -1, 0, 1, 2):
                for dk in (-2, -1, 0, 1, 2):
                    ok, _ = score(bits, idx, obs, feat, o, k + dk * sk, phi + dp * sp, alpha)
                    if ok > best[0]:
                        best = (ok, phi + dp * sp, k + dk * sk); imp = True
    return best


for mode in ("high", "edge"):
    print(f"--- feature = cumulative {mode} count ---")
    for alpha in (0.0, 15.625, 31.25, 46.875, 62.5, -31.25, -62.5):
        tot_ok = tot_n = 0
        for d in D:
            if d["pattern"] not in ("p55", "sparse", "ones", "aa", "rnd1", "zeros"):
                continue
            feat = cum_feature(d["obs"], mode)
            ok, phi, k = fit_cap(d["bits"], d["idx"], d["obs"], feat, O, alpha)
            _, n = score(d["bits"], d["idx"], d["obs"], feat, O, k, phi, alpha)
            tot_ok += ok; tot_n += n
        print(f"  alpha={alpha:8.2f} ns : {tot_ok}/{tot_n} = {tot_ok/tot_n:.4f}")
