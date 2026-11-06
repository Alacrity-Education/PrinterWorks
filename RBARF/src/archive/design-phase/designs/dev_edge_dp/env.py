"""Temperature-envelope sweep for edge_dp on the faithful synthetic sampler.

Reports, per eps:
  * frac of bits with ZERO discriminating samples  (information limit --
    no technique can recover these without an external prior)
  * mean |dead-zone| in bit-phase, largest inter-sample gap
  * edge_dp exact-frame rate and payload bit error
"""
import sys
import time

import numpy as np

import dp2
import synth2

meta, rcaps = dp2.CM.load()
PAY = {}
for c in rcaps:
    if c["pattern"] not in PAY:
        b = c["bits"]
        PAY[c["pattern"]] = bytes(int("".join(map(str, b[i * 8:i * 8 + 8])), 2)
                                  for i in range(4, 20))
print(f"{len(PAY)} patterns")

WES = [32.0, 24.0, 28.0, 18.0, 12.0, 38.0, 26.0, 46.0]
KG = tuple(np.arange(-0.006, 0.0031, 0.00025))
CFG = dict(kgrid=KG, dlo=-900.0, dhi=900.0, d0sig=1000.0, we=25.0,
           floor=0.01, dstep=12.5, vpen=1.2, vmax=25.0, vstep=6.25,
           wes=WES, sr=40.0, dr=-28.0)
PHASES = [80.0, 300.0, 520.0]
H0, H1 = synth2.H0, synth2.H1
EPS = [-0.08, -0.075, -0.05, -0.025, -0.01, 0.0, 0.01, 0.025, 0.05, 0.075, 0.08]
PHASES = [80.0, 300.0, 520.0]
DO_DP = "--info" not in sys.argv

print(f"{'eps':>7s} {'0-disc%':>8s} {'maxgap':>7s} {'EXACT':>9s} {'biterr':>9s} {'t':>5s}")
for eps in EPS:
    t0 = time.time()
    nzero = nbits = 0
    nex = ntot = nbe = 0
    gaps = []
    for name, pay in PAY.items():
        for ph in PHASES:
            c = synth2.as_cap(pay, key=f"{name}_{ph:.0f}", eps=eps, t0=ph)
            # --- information content: samples inside [h0,h1) per bit ---
            k = 1.0 / (1.0 + eps)
            A = dp2.A_of(c)
            t = ph + k * A                      # exact (oracle) time base
            j = np.floor(t / 1250.0).astype(int)
            m = (j >= 32) & (j < 160)
            u = t[m] - j[m] * 1250.0
            d = (u >= H0) & (u < H1)
            cnt = np.zeros(192)
            np.add.at(cnt, j[m], d.astype(float))
            nzero += int((cnt[32:160] == 0).sum()); nbits += 128
            gaps.append(np.diff(np.sort(t[(j >= 0) & (j < 192)])).max())
            if DO_DP:
                tot, bits, dtr, kap, k0 = dp2.run_capture(c, A, **CFG)
                true = c["bits"]
                nex += (bits[32:160] == true[32:160]).all()
                nbe += int((bits[32:160] != true[32:160]).sum())
                ntot += 1
    ex = f"{nex:3d}/{ntot:<3d}" if DO_DP else "   -   "
    be = f"{nbe/max(nbits,1):.5f}" if DO_DP else "   -   "
    print(f"{eps:+7.3f} {100*nzero/nbits:8.2f} {np.mean(gaps):7.0f} {ex:>9s} "
          f"{be:>9s} {time.time()-t0:5.0f}")
    sys.stdout.flush()
