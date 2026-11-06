#!/usr/bin/env python3
"""v2.3 MARKER-SPLIT STUDY -- which 3+3 / 4+2 / 2+4 arrangement of the six
marker bytes locks best?

The owner fixed the SIZING (6 marker bytes, 3 header + 3 trailer by
default) but not the specific bytes, so this compares the three candidate
splits on lock and geometry quality before the constant is frozen
everywhere else:

  (a) 3+3   HEADER = FF AA 65      TRAILER = 9A 55 FF     <- spec default
  (b) 4+2   HEADER = FF 00 AA 65   TRAILER = 9A FF
  (c) 2+4   HEADER = FF 65         TRAILER = 9A 55 00 FF

All three are 6 marker bytes, so the v2.3 frame is 3 + 22 + 3 = 28 bytes
= 224 bits in every case (test geometry: 16 DATA + 6 check).  The frame
LENGTH -- the constraint the seed lock actually solves -- is therefore
identical, and any difference measured here comes purely from where the
marker EDGES sit at the two ends of the burst.

Pipeline: recon/synth.py's calibrated sampler (the model fitted to the 54
real captures) -> the Python reference decoder's lock stage
(embedded_v2._seed + ._refine x2, exactly as decode_state runs it), then
its marker-forced calibration and decision passes for the geometry
metrics.  The chase is NOT run: v2.3's CRC16 chase is out of scope here
and would confound a lock comparison.

Metrics per case
  lock            _seed returned a K inside [K_MIN, K_MAX]      (else R1)
  eps error       |K_NOM/K - 1 - eps_true|, percentage points
  t0 error        |(tau - BIAS_U)*TU_ns - t0_true|, ns
  violations      marker bits decoded against the template     (-> R2)
  infeasible      leading-ones hypotheses out of range         (-> R3)
  label_err       marker-forced label mismatches               (-> R4)
  bit errors      payload' bits decoded wrong (ground truth known)
  cal n0/n1       marker-forced width samples the calibrator got

Sweep: eps -8..+8 % x t0 over the MEASURED 375-736 ns arm-phase spread
(MARGIN_INVESTIGATION.md SS4 p10-p90; median 560 ns) x all 18 test
payloads x 3 splits.

STUDY ONLY: imports the shipping modules, writes nothing but its own
results file.  No bench, no simulator, no firmware.
"""

import gzip
import json
import multiprocessing as mp
import sys
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches"))
sys.path.insert(0, str(NEWIMPL / "bench"))

import embedded_v2 as EV                                    # noqa: E402
import synth                                                # noqa: E402
from crc import build_payload_v23                            # noqa: E402
from patterns import PATTERNS                                # noqa: E402

TU_NS = synth.BIT_NS / EV.BIT_U          # 1250/512 = 2.44140625 ns per TU
K_NOM = EV.K_NOM
N_ITER = 160                             # 400 us of sampler >= frame+latch

PRIMARY = {
    "a_3+3": (bytes.fromhex("FFAA65"),   bytes.fromhex("9A55FF")),
    "b_4+2": (bytes.fromhex("FF00AA65"), bytes.fromhex("9AFF")),
    "c_2+4": (bytes.fromhex("FF65"),     bytes.fromhex("9A5500FF")),
}

# Diagnostic controls -- NOT candidates, they exist only to attribute any
# (a)-vs-(b)/(c) difference to the right cause.  (b) and (c) each put a
# 00 byte back into a marker AND make the two ends unequal in length;
# these separate the two effects:
#   z3h / z3t   3+3 sizing WITH a 00 byte (header / trailer side)
#   nz4 / nz2   (b)/(c) sizing WITHOUT any 00 byte
CONTROLS = {
    "z3h_3+3": (bytes.fromhex("FF0065"),   bytes.fromhex("9A55FF")),
    "z3t_3+3": (bytes.fromhex("FFAA65"),   bytes.fromhex("9A00FF")),
    "nz4_4+2": (bytes.fromhex("FFAAAA65"), bytes.fromhex("9AFF")),
    "nz2_2+4": (bytes.fromhex("FF65"),     bytes.fromhex("9A55AAFF")),
}

SPLITS = dict(PRIMARY)
DRIFT_PTS = [0.0]

N_DATA = 16                              # bench/test geometry


def _eps_grid():
    """-8..+8 % in 0.25 % steps, refined to 0.05 % across [-0.5, +0.5] %
    (the plateau/cliff neighbourhood MARGIN_INVESTIGATION.md SS2 found)."""
    pts = {round(-0.08 + i * 0.0025, 6) for i in range(65)}
    pts |= {round(-0.005 + i * 0.0005, 6) for i in range(21)}
    return sorted(pts)


EPS_PTS = _eps_grid()
T0_PTS = [375.0 + i * (736.0 - 375.0) / 11 for i in range(12)]   # measured


def configure(hdr: bytes, trl: bytes, npp: int) -> None:
    """Point embedded_v2's frame geometry at an arbitrary marker split.

    _build() hardwires 4+4 markers, so this is the same computation with
    the header/trailer lengths free.  Everything the lock, calibration
    and decision passes read is set here.
    """
    nb = 8 * (len(hdr) + npp + len(trl))
    known = [-1] * nb
    hb, tb = EV._bits_of(hdr), EV._bits_of(trl)
    known[0:len(hb)] = hb
    known[nb - len(tb):nb] = tb
    EV.HDR, EV.TRL = hdr, trl
    EV.N_DATA = N_DATA
    EV.CHK_LEN = npp - N_DATA
    EV.NPP = npp
    EV.NB, EV.KNOWN = nb, known
    EV.PP_LO, EV.PP_HI = 8 * len(hdr), 8 * len(hdr) + 8 * npp
    EV.CHASE_EN = False                  # chase is out of scope for a lock study


def wire_frame(hdr, trl, payload):
    return hdr + payload + trl


def run_case(job):
    split, pat, data_hex, eps, t0, drift, hdr_hex, trl_hex = job
    hdr, trl = bytes.fromhex(hdr_hex), bytes.fromhex(trl_hex)
    data = bytes.fromhex(data_hex)
    payload = build_payload_v23(data)
    configure(hdr, trl, len(payload))
    fr = wire_frame(hdr, trl, payload)
    bits_true = [int(b) for byte in fr for b in f"{byte:08b}"]
    assert len(bits_true) == EV.NB

    samples = synth._simulate(bits_true, eps, drift, t0, N_ITER)

    seed = EV._seed(samples)
    if seed is None:
        return {"split": split, "pattern": pat, "eps": eps, "t0": t0,
                "drift": drift, "lock": False}
    K0, tau0, npulse = seed
    K, tau = K0, tau0
    for _ in range(2):
        K, tau = EV._refine(samples, K, tau)

    eps_seed = K_NOM / K0 - 1.0
    eps_fit = K_NOM / K - 1.0
    t0_seed = (tau0 - EV.BIAS_U) * TU_NS
    t0_fit = (tau - EV.BIAS_U) * TU_NS

    cal = EV._calibrate(samples, K, tau)
    st = EV._decide_pass(samples, K, tau, cal)
    bits = st["bits"]
    viol = sum(1 for t in range(EV.NB)
               if EV.KNOWN[t] >= 0 and bits[t] != EV.KNOWN[t])
    biterr = sum(1 for t in range(EV.PP_LO, EV.PP_HI)
                 if bits[t] != bits_true[t])
    return {
        "split": split, "pattern": pat, "eps": eps, "t0": t0,
        "drift": drift, "lock": True, "npulse": npulse,
        "K": K, "tau": tau,
        "eps_err_seed": abs(eps_seed - eps) * 100.0,
        "eps_err": abs(eps_fit - eps) * 100.0,
        "t0_err_seed": abs(t0_seed - t0),
        "t0_err": abs(t0_fit - t0),
        "violations": viol,
        "infeasible": st["infeasible"],
        "label_err": st["label_err"],
        "biterr": biterr,
        "n_weak": st["n_weak"], "n_tied": st["n_tied"],
        "cal_n0": cal.n0, "cal_n1": cal.n1,
        "h0c": cal.h0c, "h1c": cal.h1c,
        # would the R1..R4 gates pass?  (R5+ need the v2.3 chase)
        "gates_ok": (viol == 0 and st["infeasible"] <= EV.GATE_INFEAS
                     and st["label_err"] <= EV.GATE_LABERR),
    }


def jobs():
    for split, (hdr, trl) in SPLITS.items():
        for pat, data in PATTERNS.items():
            for eps in EPS_PTS:
                for t0 in T0_PTS:
                    for dr in DRIFT_PTS:
                        yield (split, pat, data.hex(), eps, t0, dr,
                               hdr.hex(), trl.hex())


def main():
    global SPLITS, EPS_PTS, T0_PTS, DRIFT_PTS
    mode = sys.argv[1] if len(sys.argv) > 1 else "primary"
    if mode == "controls":
        SPLITS = dict(PRIMARY, **CONTROLS)
        out_name = "marker_split_controls.jsonl"
    elif mode == "drift":
        # the SS4 within-capture drift case, both signs, on the plateau
        # and at both far corners -- the stated rationale for a ruler at
        # BOTH ends is drift across the frame, so test exactly that.
        DRIFT_PTS = [-0.004, -0.002, 0.002, 0.004]
        EPS_PTS = [-0.075, -0.05, -0.025, -0.011, -0.005, 0.0,
                   0.005, 0.025, 0.05, 0.075]
        out_name = "marker_split_drift.jsonl"
    elif mode == "primary":
        out_name = "marker_split_results.jsonl"
    else:
        raise SystemExit("mode must be primary | controls | drift")
    js = list(jobs())
    print(f"[{mode}] {len(js)} cases: {len(SPLITS)} splits x "
          f"{len(PATTERNS)} payloads x {len(EPS_PTS)} eps x "
          f"{len(T0_PTS)} t0 x {len(DRIFT_PTS)} drift")
    for name, (h, t) in SPLITS.items():
        npp = N_DATA + 6
        print(f"  {name}: HDR {h.hex().upper():8s} TRL {t.hex().upper():8s} "
              f"frame {len(h) + npp + len(t)} B = "
              f"{8 * (len(h) + npp + len(t))} bits")
    # gzip: the three sweeps are ~87 MB of JSONL raw, ~8.7 MB compressed,
    # and the analyzer reads either form.
    out = Path(__file__).parent / (out_name + ".gz")
    n = 0
    with mp.Pool(20) as pool, gzip.open(out, "wt") as f:
        for r in pool.imap_unordered(run_case, js, chunksize=32):
            f.write(json.dumps(r) + "\n")
            n += 1
            if n % 2000 == 0:
                print(f"  {n}/{len(js)}")
    print(f"wrote {out} ({n} cases)")


if __name__ == "__main__":
    main()
