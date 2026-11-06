"""Alternate stage A (slot geometry, free time base) and stage B (regress
the free time base onto the parametric, phase-locking form)."""
import json, time, numpy as np, model, fit7
from model import wire_levels
CY = 62.5

def main():
    meta, caps = model.load(); caps = fit7.prepare(caps)
    d = json.load(open("stageA.json"))
    o, h1, h0 = d["o"], d["h1"], d["h0"]
    w = [0.0, -CY, 0.0, 2*CY, 0.0, 0.0, 0.0, CY]
    G = 2529.6
    n = sum(sum(len(v) for v in c["loop"].values()) for c in caps)
    for outer in range(6):
        t = time.time(); Ts = {}; ceil = 0
        for c in caps:
            sc, T = fit7.dp_path(c, o, w, h1, h0, G=G, half=2200., step=1.0, dl=150.)
            Ts[c["key"]] = T; ceil += sc
        span = 120.0 if outer == 0 else 40.0
        o, h1, h0 = fit7.profile(caps, Ts, o, w, h1, h0, span=span, step=0.25)
        m, _ = fit7.count(caps, Ts, o, w, h1, h0)
        wn, par, rms = fit7.stageB(caps, Ts)
        Gs = [par[c["key"]][1] for c in caps]
        print(f"[{outer}] dp={100*ceil/n:.3f}% prof={100*m/n:.3f}% rms={rms:.1f} "
              f"G={np.mean(Gs):.2f}\n   o={[round(x,2) for x in o]} "
              f"h1={h1:.2f} h0={h0:.2f}\n   w_cy={[round(x/CY,3) for x in wn]}",
              flush=True)
        w = [round(x/CY)*CY for x in wn]
        G = float(np.mean(Gs))
    json.dump({"o": o, "h1": h1, "h0": h0, "w": w, "G": G,
               "par": {k: [float(a), float(b)] for k, (a, b) in par.items()},
               "T": {k: list(map(float, v)) for k, v in Ts.items()}},
              open("stageAB.json", "w"))

if __name__ == "__main__":
    main()
