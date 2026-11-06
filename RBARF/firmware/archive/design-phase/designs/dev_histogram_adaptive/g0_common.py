"""Shared helpers for histogram_adaptive exploration (analysis only)."""
import json
import sys
from pathlib import Path

import numpy as np

R = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(R))
from harness import load_dataset, linearize  # noqa: E402

BIT = 1250.0
HDR = bytes.fromhex("FF00AA65")
TRL = bytes.fromhex("9A5500FF")
CAL = json.load(open(R / "approaches/dev_calibration/final.json"))

# nominal (documented, scaled to a 40-cycle loop) slot offsets, ns
NOM_O = [p * 62.5 for p in (1, 5, 9, 13, 17, 21, 27, 32)]
NOM_G = 2500.0
CAL_O = CAL["o"]
CAL_G = CAL["G"]


def frame_bits(payload_hex):
    fr = HDR + bytes.fromhex(payload_hex) + TRL
    return np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)],
                    dtype=np.int8)


def load_all():
    meta, caps = load_dataset()
    out = []
    for c in caps:
        s = linearize(c["capture"])
        it = np.array([a for a, _, _ in s], dtype=np.int64)
        sl = np.array([b for _, b, _ in s], dtype=np.int64)
        lv = np.array([v for _, _, v in s], dtype=np.int8)
        key = f"{c['pattern']}_{c['rep']}"
        # calibrated TRUTH time base
        Hc = np.zeros((len(it), 8))
        run = np.zeros(8)
        for m in range(len(it)):
            Hc[m] = run
            run[sl[m]] += lv[m]
        A = it * CAL_G + np.asarray(CAL_O)[sl] + Hc @ np.asarray(CAL["w"])
        t0, k = CAL["nuis"][key][:2]
        ttrue = t0 + k * A
        out.append(dict(key=key, pattern=c["pattern"], rep=c["rep"],
                        it=it, sl=sl, lv=lv, bits=frame_bits(c["payload"]),
                        ttrue=ttrue, payload=c["payload"]))
    return meta, out


def edge_list(lv):
    """Indices j where lv[j] != lv[j-1]; returns list of (kind, j-1, j)."""
    d = np.nonzero(lv[1:] != lv[:-1])[0]
    return [("R" if lv[j + 1] else "F", int(j), int(j + 1)) for j in d]


def coord(it, sl, o, G):
    """Blind receiver coordinate in nominal ns (no per-capture scale)."""
    return it * G + np.asarray(o, float)[sl]
