"""Stage A: fit the shared slot geometry with a free-running time base."""
import json, time, numpy as np, model, fit7
from model import wire_levels

def run():
    meta, caps = model.load(); caps = fit7.prepare(caps)
    o = [62.5,312.5,562.5,812.5,1062.5,1312.5,1687.5,2000.0]
    w = [0.0]*8; h1, h0 = 750.0, 375.0
    for r in range(10):
        t = time.time(); Ts = {}; ceil = 0; n = 0
        for c in caps:
            sc, T = fit7.dp_path(c, o, w, h1, h0, half=2200., step=1.0, dl=150.)
            Ts[c["key"]] = T; ceil += sc
            n += sum(len(v) for v in c["loop"].values())
        span = 300.0 if r < 3 else 60.0
        o, h1, h0 = fit7.profile(caps, Ts, o, w, h1, h0, span=span, step=0.25)
        m, _ = fit7.count(caps, Ts, o, w, h1, h0)
        print(f"A{r}: dp={100*ceil/n:.3f}% prof={100*m/n:.3f}% "
              f"o={[round(x,2) for x in o]} h1={h1:.2f} h0={h0:.2f} "
              f"[{time.time()-t:.0f}s]", flush=True)
    json.dump({"o": o, "h1": h1, "h0": h0, "w": w,
               "T": {k: list(map(float, v)) for k, v in Ts.items()}},
              open("stageA.json", "w"))

if __name__ == "__main__":
    import fit7
    fit7.profile.__defaults__ = (140.0, 0.25)
    run()
