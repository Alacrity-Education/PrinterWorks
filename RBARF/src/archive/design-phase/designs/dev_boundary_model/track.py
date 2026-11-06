"""Per-loop time-base tracking with a total-variation prior (Viterbi).

state  = time offset delta of loop i on a 5 ns grid
cost   = (# samples of loop i whose predicted level disagrees) + LAM*|d-d'|

The TV prior stops the 8 binary samples of one loop from buying an
arbitrarily large shift, which the unconstrained per-loop argmin does.
Used here as an ORACLE (it reads the true bits) to measure how much
information the grid really carries; the decoder-side version scores
against bit hypotheses instead.
"""
import numpy as np
from common import sample_times

DEL = np.arange(-500, 501, 5.0)
LAM = 0.02          # mismatch-units per ns of loop-to-loop clock step


def _l1_dt(f, step, lam):
    """min over j of f[j] + lam*|x_i - x_j| on a uniform grid."""
    g = f.copy()
    c = lam * step
    for i in range(1, len(g)):
        g[i] = min(g[i], g[i - 1] + c)
    for i in range(len(g) - 2, -1, -1):
        g[i] = min(g[i], g[i + 1] + c)
    return g


def track(cap, phi, P, u, nloop=None, lam=LAM):
    t0 = sample_times(cap, phi, P, u)
    it = cap.it.astype(int)
    E = cap.E
    N = (it.max() + 1) if nloop is None else nloop
    step = DEL[1] - DEL[0]
    cost = np.zeros((N, len(DEL)))
    for i in range(N):
        m = it == i
        if not m.any():
            continue
        tt = t0[m][:, None] + DEL[None, :]
        pred = np.searchsorted(E, tt.ravel(), side="right").reshape(tt.shape) & 1
        cost[i] = (pred != cap.lev[m][:, None]).sum(0)
    # forward DP
    F = np.zeros_like(cost)
    F[0] = cost[0]
    for i in range(1, N):
        F[i] = cost[i] + _l1_dt(F[i - 1], step, lam)
    # backtrack
    d = np.zeros(N)
    j = int(np.argmin(F[N - 1]))
    d[N - 1] = DEL[j]
    for i in range(N - 2, -1, -1):
        cand = F[i] + lam * np.abs(DEL - d[i + 1])
        j = int(np.argmin(cand))
        d[i] = DEL[j]
    mism = sum(int(cost[i][int(np.argmin(np.abs(DEL - d[i])))]) for i in range(N))
    t = t0.copy()
    for i in range(N):
        t[it == i] = t0[it == i] + d[i]
    return t, d, mism
