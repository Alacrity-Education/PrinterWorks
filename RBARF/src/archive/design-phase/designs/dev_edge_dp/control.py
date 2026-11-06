"""Control: run the same joint fit on SYNTHETIC captures whose generative
model is exactly the linear model we fit.  If the fitter recovers ~100%
there, the fitter is sound and the real captures carry extra structure.
"""
import sys, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import model as M
import nfit
import synth

PATTERNS = {
    "zeros": bytes(16), "ones": bytes([0xFF] * 16),
    "aa": bytes([0xAA] * 16), "p55": bytes([0x55] * 16),
    "sparse": bytes([0x01, 0x00, 0x00, 0x80] * 4),
    "rnd1": bytes([0x3C, 0x91, 0x07, 0xE2, 0x5A, 0xB6, 0x48, 0xD3,
                   0x1F, 0x60, 0xAC, 0x75, 0x89, 0x0E, 0xF4, 0x22]),
}


def build(payload, eps, phase, t1h, t0h):
    # replicate synth.synth_capture but with our T1H/T0H
    bits = M.frame_bits(payload)
    out = []
    for i in range(640):
        for s, pos in enumerate(synth.SLOT_POS_CY):
            if i == 639 and s >= 6:
                break
            cy = i * synth.LOOP_CY + pos
            t = phase + cy * 62.5 / (1.0 + eps)
            out.append((i, s, M.level_at(bits, t, t1h, t0h)))
    return out


for t1h, t0h in ((750.0, 375.0), (700.0, 350.0)):
    print(f"=== synth with T1H={t1h} T0H={t0h}, fitted with 750/375 ===")
    caps = []
    for name, pay in PATTERNS.items():
        s = build(pay, -0.003, 100.0, t1h, t0h)
        caps.append(dict(pattern=name, rep=0, payload=pay,
                         idx=[(i, sl) for i, sl, _ in s],
                         obs=[v for _, _, v in s], bits=M.frame_bits(pay)))
    C = nfit.prep(caps)
    o = np.array(M.O_NOM)
    nuis = [nfit.fit_cap(c, o) for c in C]
    for c, (m, p, k) in zip(C, nuis):
        a, n = nfit.agree(c, o, k, p)
        print(f"  {c['name']:10s} {a}/{n}={a/n:.4f} phi={p:7.1f} k={k:.5f}")
