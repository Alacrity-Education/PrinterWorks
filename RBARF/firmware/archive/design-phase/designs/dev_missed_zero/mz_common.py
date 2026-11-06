"""missed_zero exploration: time base from the calibration model + pulse/gap structures."""
import sys, json
from pathlib import Path
import numpy as np

RECON = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(RECON))
from harness import load_dataset, linearize  # noqa: E402

BIT = 1250.0
T0H = 350.0
T1H = 700.0
HEADER = bytes([0xFF, 0x00, 0xAA, 0x65])
TRAILER = bytes([0x9A, 0x55, 0x00, 0xFF])
NBITS = 192

CAL = json.load(open(Path(__file__).parent / "calib_final.json"))
G = CAL["G"]; O = np.array(CAL["o"]); W = np.array(CAL["w"])
H1M = CAL["h1"]; H0M = CAL["h0"]


def bits_of(fb):
    return [(b >> (7 - k)) & 1 for b in fb for k in range(8)]


def wire_levels(t, bits, h1=T1H, h0=T0H):
    bn = np.asarray(bits, np.int8)
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < len(bn))
    kc = np.clip(k, 0, len(bn) - 1)
    hi = np.where(bn[kc] == 1, h1, h0)
    return ((t - k * BIT) < hi) & ok


def cap_arrays(c):
    s = linearize(c["capture"])
    it = np.array([i for i, _, _ in s], float)
    sl = np.array([x for _, x, _ in s], int)
    lv = np.array([v for _, _, v in s], bool)
    return it, sl, lv


def hc_matrix(sl, lv):
    n = len(sl)
    Hc = np.zeros((n, 8))
    run = np.zeros(8)
    for m in range(n):
        Hc[m] = run
        run[sl[m]] += lv[m]
    return Hc


def A_of(it, sl, Hc):
    return it * G + O[sl] + Hc @ W


def load(pattern=None, rep=None):
    meta, caps = load_dataset()
    out = [c for c in caps
           if (pattern is None or c["pattern"] == pattern)
           and (rep is None or c["rep"] == rep)]
    return meta, out


def prepare(c, nuis=None):
    it, sl, lv = cap_arrays(c)
    Hc = hc_matrix(sl, lv)
    A = A_of(it, sl, Hc)
    fr = bytes.fromhex(c["frame"])
    bits = bits_of(fr)
    key = f"{c['pattern']}_{c['rep']}"
    if nuis is None:
        nuis = CAL["nuis"]
    t0, k = nuis[key][0], nuis[key][1]
    t = t0 + k * A
    return dict(cap=c, key=key, it=it, sl=sl, lv=lv, A=A, t=t,
                bits=bits, frame=fr, t0=t0, k=k)


def pulse_runs(lv):
    """[(i0,i1)] index ranges of contiguous HIGH samples."""
    out = []
    n = len(lv)
    i = 0
    while i < n:
        if lv[i]:
            j = i
            while j + 1 < n and lv[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out
