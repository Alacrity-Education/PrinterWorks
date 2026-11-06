"""Full blind clock_stretch pipeline + a deliberately naive bit slicer,
to measure what the clock estimate alone is worth.

Stages
  A  coarse periodogram scan over the +/-8% envelope     -> L_coarse
  B  iterated closest-bit least squares (rising edges)   -> (phi, L)
  C  integer bit-origin resolution from the trigger      -> k=0 anchor
  D  header/trailer verification (FF 00 AA 65 / 9A 55 00 FF)
  E  naive slicer: per bit, high-sample count in the predicted window
"""
import numpy as np
from common import load_all, BIT_NS
from exp6_residual_decomp import rise_events

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
LREF = 2499.6
BIAS_F = np.array([-296.3, -530.4, 444.1, 168.5,
                   -63.6, -346.1, 539.5, 84.3]) / LREF     # fraction of L
NB = 192
HDR = [1]*8 + [0]*8 + [1,0]*4 + [0,1,1,0,0,1,0,1]
TRL = [1,0,0,1,1,0,1,0] + [0,1]*4 + [0]*8 + [1]*8


def coarse(cap, Lgrid, a=A, bf=BIAS_F):
    idx, u0, u1, s0 = rise_events(cap, a)
    umid = 0.5 * (u0 + u1); g = u1 - u0
    best = (-1.0, Lgrid[0])
    prof = np.empty(len(Lgrid))
    for k, L in enumerate(Lgrid):
        t = umid * L + bf[s0] * L
        w = np.sinc(g * L / BIT_NS)
        v = abs((w * np.exp(2j*np.pi*t/BIT_NS)).sum()) / np.abs(w).sum()
        prof[k] = v
        if v > best[0]:
            best = (v, L)
    return best[1], best[0], prof


def refine(cap, L0, a=A, bf=BIAS_F, iters=20, phi0=0.0):
    idx, u0, u1, s0 = rise_events(cap, a)
    umid = 0.5 * (u0 + u1)
    L, phi = L0, phi0
    for _ in range(iters):
        b = bf[s0] * L
        t = phi + umid * L + b
        k = np.round(t / BIT_NS)
        keep = np.abs(k * BIT_NS - t) < 0.45 * BIT_NS
        X = np.vstack([np.ones(keep.sum()), umid[keep]]).T
        sol, *_ = np.linalg.lstsq(X, (k * BIT_NS - b)[keep], rcond=None)
        phi, L = sol
    b = bf[s0] * L
    t = phi + umid * L + b
    k = np.round(t / BIT_NS)
    return phi, L, (k * BIT_NS - t)[keep], k, umid, s0


def sample_times(cap, phi, L, a=A):
    return phi + (cap["it"] + a[cap["slot"]]) * L


def slice_bits(cap, phi, L, k0):
    """Naive: bit k window = [ (k+k0)*1250, (k+k0+1)*1250 ); decide by the
    number of high samples inside (>=2 -> 1, ==0 -> 0, ==1 -> ambiguous)."""
    t = sample_times(cap, phi, L) - k0 * BIT_NS
    lev = cap["lev"]
    kk = np.floor(t / BIT_NS).astype(int)
    bits, conf = [], []
    for k in range(NB):
        m = (kk == k)
        n = int(lev[m].sum()); tot = int(m.sum())
        if tot == 0:
            bits.append(0); conf.append(0); continue
        bits.append(1 if n >= 2 else 0)
        conf.append(n)
    return np.array(bits), np.array(conf)


def hdr_score(bits):
    a = sum(int(b == c) for b, c in zip(bits[:32], HDR))
    b = sum(int(x == c) for x, c in zip(bits[160:192], TRL))
    return a + b


if __name__ == "__main__":
    meta, caps = load_all()
    Lgrid = np.arange(2300.0, 2705.0, 2.0)
    print(f"{'pattern':11s} {'rep':>3s} {'Lc':>8s} {'J':>6s} {'L':>8s} "
          f"{'phi':>7s} {'rms':>5s} {'max':>6s} {'k0':>3s} {'hdr':>3s} "
          f"{'bitErr':>6s} {'byteOK':>6s}")
    tot_bit = 0; tot_exact = 0; maxres = []
    for cap in caps:
        Lc, Jv, prof = coarse(cap, Lgrid)
        phi, L, res, k, umid, s0 = refine(cap, Lc)
        # integer bit origin: try a few and keep the best header/trailer score
        best = None
        for k0 in (-2, -1, 0, 1, 2):
            bits, conf = slice_bits(cap, phi, L, k0)
            sc = hdr_score(bits)
            if best is None or sc > best[0]:
                best = (sc, k0, bits, conf)
        sc, k0, bits, conf = best
        truth = cap["bits"]
        bit_err = int((bits != truth).sum())
        pay = bytes(int("".join(map(str, bits[32+8*i:40+8*i])), 2) for i in range(16))
        ok = pay == bytes.fromhex(cap["payload"])
        tot_bit += bit_err; tot_exact += ok
        maxres.append(np.abs(res).max())
        print(f"{cap['pattern']:11s} {cap['rep']:3d} {Lc:8.1f} {Jv:6.3f} "
              f"{L:8.2f} {phi:7.1f} {np.sqrt((res**2).mean()):5.1f} "
              f"{np.abs(res).max():6.1f} {k0:3d} {sc:3d} {bit_err:6d} "
              f"{str(ok):>6s}")
    print(f"\nTOTAL naive-slicer: exact {tot_exact}/54, bit errors {tot_bit}"
          f" / {54*192}")
    print(f"max |rising-edge residual| : mean={np.mean(maxres):.1f} "
          f"worst={np.max(maxres):.1f} ns")
