"""Envelope sweep: blind-bit count vs receiver clock error, from geometry.

tau = 62.5/(1+eps); loop = LOOP_CY*tau; slot s of loop i at
t = rho + tau*(LOOP_CY*i + C[s]).  A bit is BLIND when no sample lands in
its decision window [T0H, T1H) = [375, 750) ns.
"""
import numpy as np

C = np.array([1, 5, 9, 13, 17, 21, 27, 31], float)
LOOP_CY = 40
BIT = 1250.0
H0, H1 = 375.0, 750.0
NBITS = 192
PAY = np.arange(32, 160)


def blind_bits(eps, rho, drift=0.0):
    tau = 62.5 / (1.0 + eps)
    n = int(np.ceil((NBITS * BIT) / (LOOP_CY * tau))) + 2
    i = np.arange(n)[:, None]
    cy = LOOP_CY * i + C[None, :]
    if drift:
        f = 1.0 + drift * (cy / cy.max())
        t = rho + 62.5 * cy / ((1.0 + eps) * f)
    else:
        t = rho + tau * cy
    t = t.ravel()
    j = np.floor(t / BIT).astype(int)
    p = t - j * BIT
    inf = (p >= H0) & (p < H1) & (j >= 0) & (j < NBITS)
    seen = np.zeros(NBITS, bool)
    seen[j[inf]] = True
    nsamp = np.zeros(NBITS, int)
    np.add.at(nsamp, j[inf], 1)
    blind = np.nonzero(~seen)[0]
    return blind, nsamp


def runs(idx):
    out, cur = [], []
    for b in sorted(idx):
        if cur and b == cur[-1] + 1:
            cur.append(b)
        else:
            if cur:
                out.append(cur)
            cur = [b]
    if cur:
        out.append(cur)
    return out


def main():
    gaps_cy = list(np.diff(C)) + [LOOP_CY - C[-1] + C[0]]
    print("gaps (cycles):", [int(g) for g in gaps_cy])
    print("%-8s %10s %10s %8s %8s %8s" %
          ("eps", "gap5_6 ns", "gap7_0 ns", "blind", "worst", "maxrun"))
    for eps in (-0.08, -0.075, -0.05, -0.025, -0.01, -0.003, 0.0,
                0.01, 0.025, 0.05, 0.075, 0.08):
        tau = 62.5 / (1 + eps)
        res = []
        for rho in np.arange(0.0, 2 * tau, 4.0):
            b, _ = blind_bits(eps, rho)
            pb = [x for x in b if 32 <= x < 160]
            res.append((len(pb), max([len(r) for r in runs(pb)] or [0])))
        m = np.array(res)
        print("%-8s %10.1f %10.1f %8.1f %8d %8d"
              % (f"{eps:+.3f}", 6 * tau, (LOOP_CY - C[-1] + C[0]) * tau,
                 m[:, 0].mean(), m[:, 0].max(), m[:, 1].max()))

    print("\nblind-bit count vs phase rho at the two corners and the bench:")
    for eps in (-0.075, -0.003, 0.075):
        tau = 62.5 / (1 + eps)
        row = []
        for rho in np.arange(0.0, 2 * tau, 12.5):
            b, _ = blind_bits(eps, rho)
            row.append(len([x for x in b if 32 <= x < 160]))
        print(f"  eps={eps:+.3f}: " + " ".join(f"{v:3d}" for v in row))

    print("\nwithin-capture drift +-0.2% at the slow corner:")
    for dr in (-0.002, 0.0, 0.002):
        vals = [len([x for x in blind_bits(-0.075, rho, dr)[0] if 32 <= x < 160])
                for rho in np.arange(0.0, 135.0, 4.0)]
        print(f"  drift {dr:+.3f}: mean {np.mean(vals):.1f} max {max(vals)}")

    print("\nsamples-per-bit inside the decision window (bench, rho=63):")
    _, ns = blind_bits(-0.003, 63.0)
    import collections
    print("  ", dict(sorted(collections.Counter(ns[32:160]).items())))
    for eps in (-0.075, 0.075):
        _, ns = blind_bits(eps, 63.0)
        print(f"   eps={eps:+.3f}",
              dict(sorted(collections.Counter(ns[32:160]).items())))


if __name__ == "__main__":
    main()
