"""Per-loop phase tracking with continuity unwrapping + plateau intervals."""
import numpy as np

from bm_common import load, wire_level

CY = 62.5
DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) * CY
GRID = np.arange(-1300.0, 2600.0, 1.0)


def loop_profile(c, i, O, h1, h0):
    m = c["it"] == i
    s = c["sl"][m]
    v = c["lv"][m]
    base = 2500.0 * i + O[s]
    nb = np.array([int(np.count_nonzero(wire_level(base + p, c["bits"], h1, h0) != v))
                   for p in GRID])
    return nb


def intervals(mask, grid):
    out = []
    k = 0
    n = len(mask)
    while k < n:
        if mask[k]:
            j = k
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((grid[k], grid[j]))
            k = j + 1
        else:
            k += 1
    return out


def track(c, O=DOC, h1=750.0, h0=375.0, nloops=96):
    phis = []
    prev = None
    rows = []
    for i in range(nloops):
        nb = loop_profile(c, i, O, h1, h0)
        lo = nb.min()
        iv = intervals(nb == lo, GRID)
        # pick interval whose centre is nearest prev (continuity)
        if prev is None:
            k = int(np.argmin([abs((a + b) / 2 - 200.0) for a, b in iv]))
        else:
            k = int(np.argmin([min(abs((a + b) / 2 - prev),
                                   abs((a + b) / 2 - prev + 1250),
                                   abs((a + b) / 2 - prev - 1250)) for a, b in iv]))
        a, b = iv[k]
        ctr = (a + b) / 2
        for w in (-1250.0, 0.0, 1250.0):
            if prev is None:
                break
            if abs(ctr + w - prev) < abs(ctr - prev):
                a, b, ctr = a + w, b + w, ctr + w
        prev = ctr
        phis.append(ctr)
        rows.append((i, lo, a, b, len(iv)))
    return np.array(phis), rows


def main():
    meta, caps = load()
    print("%-14s %8s %8s %8s %7s %7s %6s" %
          ("key", "phi0", "phi95", "drift", "G_lin", "resid", "badloops"))
    for c in caps:
        phi, rows = track(c)
        n = 96
        x = np.arange(n)
        # only loops fully inside the frame
        sel = x < 94
        A = np.vstack([np.ones(sel.sum()), x[sel]]).T
        coef, *_ = np.linalg.lstsq(A, phi[sel], rcond=None)
        pred = A @ coef
        resid = float(np.max(np.abs(phi[sel] - pred)))
        badl = sum(1 for r in rows[:94] if r[1] > 0)
        print("%-14s %8.0f %8.0f %8.0f %7.1f %7.0f %6d" %
              (c["key"], phi[0], phi[93], phi[93] - phi[0],
               2500.0 + coef[1], resid, badl))


if __name__ == "__main__":
    main()
