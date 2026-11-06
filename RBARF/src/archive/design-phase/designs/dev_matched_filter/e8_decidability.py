"""E8: purely geometric decidability of a bit cell under the anchored
matched filter, swept across the HSI envelope.

For a cell starting at wire time T, the samples landing in [T, T+1250) have
phases p.  A sample discriminates 0 from 1 iff h0 <= p < h1 (predicted low
for '0', high for '1').  Samples with p < h0 or p >= h1 confirm the anchor
but say nothing about the bit.

    n_dis(cell)  = #samples with phase in [h0, h1)
    n_dis_g      = same but with a guard band `GUARD` excluded at each edge
                   (edge smear + anchor error)
"""
import numpy as np

BIT = 1250.0
G_CY = 40.0
P_CY = np.array([0., 4., 8., 12., 16., 20., 26., 31.])
H1, H0 = 750.0, 375.0
GUARD = 60.0


def cell_stats(eps, phase_ns, h1=H1, h0=H0, guard=0.0, nbits=192,
               P=P_CY, G=G_CY, cy=62.5):
    """Return per-bit n_dis over the whole frame for one (eps, phase)."""
    kap = cy / (1.0 + eps)                      # ns per nominal cycle
    nloop = int(nbits * BIT / (kap * G)) + 3
    it = np.repeat(np.arange(nloop), 8)
    sl = np.tile(np.arange(8), nloop)
    t = phase_ns + kap * (it * G + P[sl])
    b = np.floor(t / BIT).astype(int)
    ph = t - b * BIT
    ok = (b >= 0) & (b < nbits)
    b, ph = b[ok], ph[ok]
    dis = (ph >= h0 + guard) & (ph < h1 - guard)
    n_dis = np.bincount(b[dis], minlength=nbits)
    n_tot = np.bincount(b, minlength=nbits)
    return n_dis, n_tot


def sweep():
    print(f"{'eps':>7} {'undec%':>8} {'undec%g':>8} {'maxrun':>7} "
          f"{'n_dis med':>10} {'samp/cell':>10} {'hdr_dis':>8} {'trl_dis':>8}")
    for eps in (-0.08, -0.075, -0.05, -0.025, -0.01, 0.0,
                0.01, 0.025, 0.05, 0.075, 0.08):
        u = ug = 0
        n = 0
        runs = []
        meds = []
        st = []
        hd = []
        tl = []
        for phase in np.arange(0.0, 250.0, 10.0):
            nd, nt = cell_stats(eps, phase)
            pay = nd[32:160]
            u += int((pay == 0).sum())
            n += len(pay)
            ndg, _ = cell_stats(eps, phase, guard=GUARD)
            ug += int((ndg[32:160] == 0).sum())
            meds.append(np.median(pay))
            st.append(np.median(nt[32:160]))
            hd.append(int(nd[:32].sum()))
            tl.append(int(nd[160:192].sum()))
            r = c = 0
            for v in pay:
                c = c + 1 if v == 0 else 0
                r = max(r, c)
            runs.append(r)
        print(f"{eps:+7.3f} {100*u/n:8.2f} {100*ug/n:8.2f} {max(runs):7d} "
              f"{np.median(meds):10.1f} {np.median(st):10.1f} "
              f"{np.median(hd):8.1f} {np.median(tl):8.1f}")


def gap_analysis():
    print("\ninter-sample gaps (ns) vs eps  [gap > 375 swallows a T0H,")
    print("gap > 500 can merge two 1-bits]")
    gaps_cy = [P_CY[i + 1] - P_CY[i] for i in range(7)] + [G_CY - P_CY[7]]
    for eps in (-0.075, 0.0, 0.075):
        kap = 62.5 / (1 + eps)
        print(f"  eps={eps:+.3f} kappa={kap:.2f} ns/cy  gaps="
              f"{[round(g*kap,1) for g in gaps_cy]}  loop={G_CY*kap:.1f}ns")


sweep()
gap_analysis()
