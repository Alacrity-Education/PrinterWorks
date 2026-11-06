"""Shared plumbing for the A_MAX x T_MAX chase-budget sweep (host only).

Everything here drives recon/approaches/embedded_v2.py -- the NORMATIVE
reference decoder -- through recon/approaches/dev_prod/v23lib.py, exactly
the way dev_suite/dw_ab_suite_failures.py drives the DW_EN A/B.  The only
overrides are A_MAX and T_MAX (and A_PAIR, which v2.3 keeps pinned to
A_MAX; _chase23 sets npair = n and never reads A_PAIR, so the override is
belt-and-braces for the compat path only).

Grid-independence shortcut (validated, see sweep_amax_tmax.py --validate):
a frame that refuses at R1/R2/R3/R4/R5 or accepts DIRECT never reads
A_MAX or T_MAX -- the admission gates (C3) and the comparison budget both
sit AFTER the direct accept in _chase23 -- so one decode answers the whole
grid for it.  Only frames that reach the chase are re-decoded per point.
"""
import sys
from pathlib import Path

NI = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NI / "recon" / "approaches" / "dev_prod"))
sys.path.insert(0, str(NI / "bench"))
sys.path.insert(0, str(NI / "recon"))
sys.path.insert(0, str(NI))

from v23lib import (load_ref, capture, linearize, set_params,   # noqa: E402
                    CAP_BYTES_PROD)

import os as _os


def _g(env, dflt):
    v = _os.environ.get(env)
    return tuple(int(x) for x in v.split(",")) if v else dflt


# RBARF_AGRID / RBARF_TGRID override the grid for the refinement passes
# (dev_amax/README notes which figure came from which grid).
A_GRID = _g("RBARF_AGRID", (11, 16, 22, 27, 40))
T_GRID = _g("RBARF_TGRID", (131, 262, 393, 524, 1048))
GRID = [(a, t) for a in A_GRID for t in T_GRID]
BASE = (11, 131)

# the production auto-trim band is -1.6..-0.4 %; these are the five
# operating points the brief names (PROD_CLOSURE SS20.3 measured
# -0.974 % mean, sd 0.029 pp, over 1 776 soak frames)
EPS_GRID = (-0.0060, -0.0080, -0.0090, -0.0105, -0.0120)
# the arm's MEASURED t0 spread on silicon, PROD_CLOSURE SS16.3: 102..650 ns
# over 79 complete bursts, and SS19.5/SS20.2 sweep 70..658 ns.  48 phases.
NT0 = 48
T0_GRID = tuple(70.0 + i * (658.0 - 70.0) / (NT0 - 1) for i in range(NT0))

# refusal causes that provably cannot depend on A_MAX/T_MAX
PRECHASE = ("refuse_lock", "refuse_marker", "refuse_infeasible",
            "refuse_labelerr", "refuse_emitgate")

CAUSE_R = {"refuse_lock": "R1", "refuse_marker": "R2",
           "refuse_infeasible": "R3", "refuse_labelerr": "R4",
           "refuse_emitgate": "R5", "refuse_nocand": "R6",
           "refuse_admit": "R7", "refuse_chase": "R8"}


def make_ref(nd):
    ev = load_ref()
    ev._configure(nd, check=True, chk=6)
    return ev


def point(ev, a, t):
    """The reference's own entry point -- embedded_v2.set_chase_budget(),
    which mirrors decode.c's A_MAX_CFG / T_MAX_CFG (and A_PAIR tracking
    A_MAX).  v23lib.set_params is kept as the fallback for a reference
    predating it."""
    if hasattr(ev, "set_chase_budget"):
        ev.set_chase_budget(a, t)
    else:
        set_params(ev, A_MAX=a, A_PAIR=a, T_MAX=t)


def outcome(ev, lin, truth):
    """-> (verdict, cause_or_path, trials, comps).  verdict in
    DELIVERED / WRONG / REFUSED / DOMAIN.

    DOMAIN = the reference's own s16/u16 range assertion fired.  That can
    only happen in P1-P3 (lock/segment/calibrate), i.e. strictly BEFORE
    the chase, on a capture so malformed that the fitted (K, tau) puts a
    segment offset outside s16.  The target's real s16 arithmetic would
    wrap instead; the reference refuses to model it.  Such a frame is
    grid-independent by construction and is counted separately, never as
    a delivery or a refusal."""
    try:
        out, info = ev.decode_ex(lin)
    except AssertionError as e:
        return "DOMAIN", str(e.args[0][0] if e.args and
                             isinstance(e.args[0], tuple) else e), 0, 0
    tr = info.get("trials") or 0
    cp = info.get("comps") or 0
    if out is None:
        return "REFUSED", info["cause"], tr, cp
    if out == truth:
        return "DELIVERED", info.get("path"), tr, cp
    return "WRONG", info.get("path"), tr, cp


def grid_outcomes(ev, lin, truth):
    """{(a, t): (verdict, tag, trials, comps)} for the whole GRID, using
    the grid-independence shortcut."""
    point(ev, *BASE)
    v0 = outcome(ev, lin, truth)
    if v0[0] == "DOMAIN":
        return {p: v0 for p in GRID}, False
    if v0[0] == "REFUSED" and v0[1] in PRECHASE:
        return {p: v0 for p in GRID}, False
    if v0[0] in ("DELIVERED", "WRONG") and v0[1] == "direct":
        return {p: v0 for p in GRID}, False
    res = {BASE: v0}
    for p in GRID:
        if p == BASE:
            continue
        point(ev, *p)
        res[p] = outcome(ev, lin, truth)
    return res, True


def grid_outcomes_full(ev, lin, truth):
    """No shortcut -- 25 real decodes.  Used by --validate."""
    res = {}
    for p in GRID:
        point(ev, *p)
        res[p] = outcome(ev, lin, truth)
    return res


def fa_bound(t, bits=16):
    return 1.0 - (1.0 - 2.0 ** -bits) ** t


def max_trials(a, t):
    """Worst-case chase trials at (A_MAX, T_MAX): the five-phase
    enumeration yields n + C(n,2) = n(n+1)/2 flip sets, and every trial
    spends at least one residual comparison out of a budget the direct
    accept already dipped into."""
    return min(a * (a + 1) // 2, t - 1)


# PROD_CLOSURE SS15.7 / ARCHITECTURE SS5.4: ~8.6 k ticks = 0.54 ms per
# chase trial (the asm tail recomputes the 384-step CRC-16 per trial
# instead of carrying an XP8 syndrome table).  Fixed pipeline cost 170 ms
# = the SS20.4 measured decode-window MEAN on silicon (min 163.7, max
# 182.9 ms over the 60-frame Lever B gate).
MS_PER_TRIAL = 0.54
MS_FIXED = 170.0


def proj_ms(trials):
    return MS_FIXED + MS_PER_TRIAL * trials
