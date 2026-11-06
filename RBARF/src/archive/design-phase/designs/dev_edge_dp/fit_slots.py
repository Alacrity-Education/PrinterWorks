"""Global slot-offset fit (coordinate descent) with per-capture (phi,k).

Metric: sample agreement restricted to the frame span [0, 192*1250) ns.
"""
import sys, json, time
import model as M

FRAME_NS = 192 * 1250.0


def in_frame_mask(o, k, phi, idx):
    return [0.0 <= phi + k * (i * M.L_NOM + o[s]) < FRAME_NS for i, s in idx]


def score_cap(bits, idx, obs, o, k, phi):
    ok = n = 0
    for (i, s), v in zip(idx, obs):
        t = phi + k * (i * M.L_NOM + o[s])
        if t < -200.0 or t >= FRAME_NS + 200.0:
            continue
        n += 1
        ok += (M.level_at(bits, t) == v)
    return ok, n


def fit_cap(bits, idx, obs, o, phi0=0.0, k0=1.003, coarse=True):
    best = (-1, 0.0, 1.0)
    if coarse:
        for k in [1.0 + 0.0004 * j for j in range(-25, 46)]:
            for phi in [x * 12.0 for x in range(-42, 43)]:
                ok, n = score_cap(bits, idx, obs, o, k, phi)
                if ok > best[0]:
                    best = (ok, phi, k)
    else:
        best = (score_cap(bits, idx, obs, o, k0, phi0)[0], phi0, k0)
    for step_phi, step_k in ((6.0, 1.5e-4), (2.0, 5e-5), (0.5, 1.5e-5), (0.25, 5e-6)):
        improved = True
        while improved:
            improved = False
            _, phi, k = best
            for dp in (-2, -1, 0, 1, 2):
                for dk in (-2, -1, 0, 1, 2):
                    if dp == 0 and dk == 0:
                        continue
                    p2, k2 = phi + dp * step_phi, k + dk * step_k
                    ok, _ = score_cap(bits, idx, obs, o, k2, p2)
                    if ok > best[0]:
                        best = (ok, p2, k2)
                        improved = True
    return best


def total(D, o, nuis):
    ok = n = 0
    for d, (_, phi, k) in zip(D, nuis):
        a, b = score_cap(d["bits"], d["idx"], d["obs"], o, k, phi)
        ok += a; n += b
    return ok, n


def main():
    meta, D = M.load()
    o = list(M.O_NOM)
    t0 = time.time()
    nuis = [fit_cap(d["bits"], d["idx"], d["obs"], o) for d in D]
    ok, n = total(D, o, nuis)
    print(f"nominal offsets: {ok}/{n} = {ok/n:.4f}   ({time.time()-t0:.0f}s)")

    for rnd in range(4):
        for s in range(1, 8):
            base = o[s]
            cands = [base + d for d in (-60, -40, -25, -15, -8, -4, 0, 4, 8, 15, 25, 40, 60)]
            bestv, besto = None, base
            for c in cands:
                if s > 0 and c <= o[s - 1] + 20:
                    continue
                if s < 7 and c >= o[s + 1] - 20:
                    continue
                o2 = list(o); o2[s] = c
                a, _ = total(D, o2, nuis)
                if bestv is None or a > bestv:
                    bestv, besto = a, c
            o[s] = besto
        nuis = [fit_cap(d["bits"], d["idx"], d["obs"], o, ph, kk, coarse=False)
                for d, (_, ph, kk) in zip(D, nuis)]
        ok, n = total(D, o, nuis)
        print(f"round {rnd}: {ok}/{n} = {ok/n:.4f}  o={[round(x,1) for x in o]}  ({time.time()-t0:.0f}s)")

    json.dump({"o": o, "nuis": [[p, k] for _, p, k in nuis],
               "caps": [f"{d['pattern']}_{d['rep']}" for d in D]},
              open("slotfit.json", "w"), indent=1)
    print("gaps ns:", [round(o[i+1]-o[i], 1) for i in range(7)] + [round(2500*1.0 - o[7] + o[0], 1)])


if __name__ == "__main__":
    main()
