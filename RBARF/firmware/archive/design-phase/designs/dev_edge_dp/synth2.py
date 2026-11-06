"""Faithful synthetic sampler for envelope work.

Unlike recon/synth.py (uniform 40-cycle loop, no data-dependent term)
this reproduces the *calibrated* sampler:

    t(i,s) = t0 + k * ( i*G + o[s] + sum_j w[j]*Hc_j(i,s) )
    k      = 1/(1+eps)

Hc_j is the running count of HIGH reads at slot j, so the time base is
causal: the level read at (i,s) is decided before it feeds back into the
timing of later samples.  Wire: 1250 ns bit, high for h1 / h0.
"""
import json
import sys
from pathlib import Path

import numpy as np

CAL = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_calibration")
F = json.load(open(CAL / "final.json"))
G, O, W, H1, H0 = F["G"], np.array(F["o"]), np.array(F["w"]), F["h1"], F["h0"]
BIT = 1250.0
NIT = 640

HDR = bytes.fromhex("FF00AA65")
TRL = bytes.fromhex("9A5500FF")


def frame_bits(payload: bytes):
    fr = HDR + payload + TRL
    return np.array([(b >> (7 - j)) & 1 for b in fr for j in range(8)], np.int8)


def level(bits, t):
    if t < 0:
        return 0
    j = int(t // BIT)
    if j >= len(bits):
        return 0
    return 1 if (t - j * BIT) < (H1 if bits[j] else H0) else 0


def synth(payload, eps=0.0, t0=300.0, jitter=0.0, seed=0, drift=0.0):
    """Returns (it, sl, lv) arrays like harness.linearize()."""
    bits = frame_bits(payload)
    k = 1.0 / (1.0 + eps)
    rng = np.random.default_rng(seed)
    Hc = np.zeros(8)
    it = []; sl = []; lv = []
    for i in range(NIT):
        for s in range(8):
            if i == NIT - 1 and s >= 6:
                break
            A = i * G + O[s] + Hc @ W
            kk = k * (1.0 + drift * (i / NIT))
            t = t0 + kk * A
            if jitter:
                t += rng.normal(0.0, jitter)
            v = level(bits, t)
            it.append(i); sl.append(s); lv.append(v)
            Hc[s] += v
    return (np.array(it, np.int32), np.array(sl, np.int32),
            np.array(lv, np.int8))


def as_cap(payload, key="synth", **kw):
    it, sl, lv = synth(payload, **kw)
    return dict(key=key, it=it, sl=sl, lv=lv, bits=frame_bits(payload),
                n=len(it), pattern=key, rep=0)


if __name__ == "__main__":
    # sanity: compare pulse-width histogram against a real capture
    sys.path.insert(0, str(CAL))
    import model as CM
    from collections import Counter
    meta, caps = CM.load()

    def widths(lv):
        w = []; run = 0
        for v in lv:
            if v:
                run += 1
            elif run:
                w.append(run); run = 0
        return Counter(w)

    for pat in ("ones", "aa", "zeros", "rnd1"):
        r = next(c for c in caps if c["pattern"] == pat and c["rep"] == 0)
        s = as_cap(bytes.fromhex("00" * 16) if pat == "zeros" else b"", key=pat)
        print(pat, "real high-run lengths:", dict(sorted(widths(r["lv"]).items())))
    for eps in (-0.075, -0.003, 0.075):
        c = as_cap(bytes([0xAA] * 16), eps=eps)
        print(f"eps={eps:+.3f} synth aa high-runs:",
              dict(sorted(widths(c["lv"]).items())))
