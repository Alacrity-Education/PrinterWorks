#!/usr/bin/env python3
"""v2.3 fuzz corpus -- deterministic, host-only, biased to exactly the
refusal classes the three relaxations open up.

Every case is a RAW capture in cap_code.s layout plus its ground-truth
DATA bytes, so the same corpus serves
  * parity_v23.py   -- decode.c must be bit-identical to embedded_v2.py
  * this file's --report mode -- accepted / correct / WRONG emissions,
    i.e. the wrong-emission rate on adversarial input.

Damage is injected ON THE WIRE (into the frame bytes before the sampler
runs), so the decoder really does see a damaged marker or a check block
whose three copies disagree -- not a doctored decoder state.

Classes (>= 80 cases at each of the test and production geometries):
  eps_wide    the clock-range class      (RELAXATION A)   eps -8..+8 %
  malform     partial-burst captures     (the real R1 shape: tail or
              head of the burst missing -- MARGIN_INVESTIGATION SS4)
  mk_damage   marker bits flipped on the wire, 1..16 of 48
              (RELAXATION B) -- includes the FIRST and LAST frame byte,
              which the owner directive says must NOT be required
  chk_damage  check-block damage, incl. the 3-copies-damaged-in-
              different-positions case and both positions SPLIT
  zerorun     long-zero-run payloads (the Klipper preset shapes that
              produced the project's only two wrong emissions)
  weakbits    operating points chosen to leave > 5 weak bits (the v2.2
              R7 admission class that RELAXATION C opens)
  drift       within-capture linear eps ramp +-0.2 / +-0.4 %
"""
import argparse
import collections
import json
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import v23lib as L                                              # noqa: E402

T0 = [375.0, 470.0, 560.0, 650.0, 736.0]


def _lcg(seed):
    x = seed & 0x7FFFFFFF
    while True:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        yield x


def _payloads(nd):
    """Deterministic payload set at DATA length nd."""
    out = []
    if nd == 48:
        for k, v in L.prod_payloads().items():
            out.append((k, v))
        kl = json.loads((SC.parents[2] / "klipper" /
                         "bench_klipper_macro_results.prefix_baseline.json")
                        .read_text())
        seen = set()
        for r in kl["rows"]:
            fr = bytes.fromhex(r["frame"])
            if len(fr) == 60 and r["case"] not in seen:
                seen.add(r["case"])
                out.append(("kl_" + r["case"], fr[4:52]))
    else:
        from patterns import PATTERNS, VAL_PATTERNS
        for k, v in list(PATTERNS.items()):
            out.append((k, v))
        for k, v in list(VAL_PATTERNS.items()):
            out.append(("val_" + k, v))
    return out


def _damaged_capture(data, eps, t0, nd, flips=(), drift=0.0, trunc=0,
                     chop=0):
    """Simulate a capture of the v2.3 frame with `flips` (frame BIT
    indices) inverted on the wire."""
    bits = L.frame_bits(data)
    for b in flips:
        bits[b] ^= 1
    ncap = L.CAP_BYTES_PROD if nd == 48 else L.CAP_BYTES_TEST
    sm = L.simulate(bits, eps, t0, ncap + 1, drift)
    raw = bytearray(L.pack(sm, ncap))
    if chop:
        raw = raw[chop:] + bytes(chop)
    if trunc:
        raw = raw[:ncap - trunc]
    return bytes(raw)


def cases(nd):
    """[(tag, raw_capture, truth_data, class)] -- deterministic."""
    pay = _payloads(nd)
    nb = 8 * (6 + nd + 6)                        # v2.3 frame bits
    hdr_bits = list(range(24))
    trl_bits = list(range(nb - 24, nb))
    chk0 = 24 + 8 * nd                           # first check-block bit
    out = []
    rnd = _lcg(0x5A3C + nd)

    # ---- eps_wide: the clock-range class ----------------------------
    for eps in (-0.08, -0.06, -0.04, -0.025, -0.02, -0.015, -0.01,
                -0.005, -0.002, 0.0, 0.002, 0.005, 0.01, 0.02, 0.04,
                0.06, 0.08):
        name, data = pay[next(rnd) % len(pay)]
        t0 = T0[next(rnd) % len(T0)]
        out.append(("eps%+.3f/%s" % (eps, name),
                    _damaged_capture(data, eps, t0, nd), data, "eps_wide"))

    # ---- malform: the REAL R1 shape (partial burst) ------------------
    for (tr, ch) in ((8, 0), (24, 0), (40, 0), (0, 2), (0, 4), (0, 8),
                     (16, 2)):
        name, data = pay[next(rnd) % len(pay)]
        out.append(("malform tr%d ch%d/%s" % (tr, ch, name),
                    _damaged_capture(data, -0.011, 560.0, nd, trunc=tr,
                                     chop=ch), data, "malform"))

    # ---- mk_damage: 1..16 marker bits flipped ON THE WIRE ------------
    #  incl. the FIRST frame byte (bits 0..7) and the LAST (nb-8..nb-1),
    #  which the owner directive says must NOT be required to validate
    mk_sets = [
        ("hdr b0", [0]),
        ("hdr b7", [7]),
        ("first byte all", list(range(8))),
        ("last byte all", list(range(nb - 8, nb))),
        ("first+last byte", list(range(8)) + list(range(nb - 8, nb))),
        ("hdr 2", [1, 9]),
        ("hdr 4", [2, 5, 11, 20]),
        ("trl 4", [nb - 24, nb - 17, nb - 9, nb - 1]),
        ("hdr+trl 8", [0, 3, 12, 19, nb - 22, nb - 14, nb - 7, nb - 2]),
        ("hdr 12", hdr_bits[:12]),
        ("hdr+trl 12", hdr_bits[:6] + trl_bits[:6]),
        ("hdr+trl 16", hdr_bits[:8] + trl_bits[:8]),
    ]
    for (lbl, fl) in mk_sets:
        for eps in (-0.011, 0.002):
            name, data = pay[next(rnd) % len(pay)]
            out.append(("mk[%s] eps%+.3f/%s" % (lbl, eps, name),
                        _damaged_capture(data, eps, 560.0, nd, flips=fl),
                        data, "mk_damage"))

    # ---- chk_damage: the per-byte-majority stress -------------------
    def cb(copy, half, bit):
        """frame bit of check copy 0..2, half 0=HI 1=LO, bit 0..7"""
        return chk0 + 8 * (2 * copy + half) + bit
    chk_sets = [
        ("one HI byte", [cb(0, 0, 1), cb(0, 0, 5)]),
        ("one copy both bytes", [cb(1, 0, 0), cb(1, 0, 4),
                                 cb(1, 1, 2), cb(1, 1, 6)]),
        ("2 copies, DIFFERENT halves", [cb(0, 0, 3), cb(1, 1, 3)]),
        ("2 copies, diff halves x2", [cb(0, 0, 1), cb(0, 0, 2),
                                      cb(2, 1, 5), cb(2, 1, 6)]),
        ("3 copies, all different halves/bits",
         [cb(0, 0, 0), cb(1, 1, 1), cb(2, 0, 2)]),
        ("HI position SPLIT (all 3 differ)",
         [cb(0, 0, 0), cb(1, 0, 1), cb(2, 0, 2)]),
        ("BOTH positions SPLIT",
         [cb(0, 0, 0), cb(1, 0, 1), cb(2, 0, 2),
          cb(0, 1, 3), cb(1, 1, 4), cb(2, 1, 5)]),
        ("all 6 check bytes damaged",
         [cb(c, h, (c + h) & 7) for c in range(3) for h in range(2)]),
    ]
    for (lbl, fl) in chk_sets:
        for eps in (-0.011, -0.002, 0.002):
            name, data = pay[next(rnd) % len(pay)]
            out.append(("chk[%s] eps%+.3f/%s" % (lbl, eps, name),
                        _damaged_capture(data, eps, 560.0, nd, flips=fl),
                        data, "chk_damage"))

    # ---- zerorun: the long-zero-run payloads ------------------------
    zr = [("all_zero", bytes(nd)),
          ("zero_then_ff", bytes(nd - 4) + b"\xff\xff\xff\xff"),
          ("ff_then_zero", b"\xff\xff\xff\xff" + bytes(nd - 4)),
          ("sparse", bytes(0x40 if i % 17 == 0 else 0 for i in range(nd)))]
    if nd == 48:
        zr += [(n, d) for (n, d) in pay if n.startswith("kl_preset_rain")
               or n.startswith("kl_preset_draw") or n == "kl_all_zero_data"]
    for (name, data) in zr:
        for eps in (-0.011, -0.004, 0.002, 0.0025, 0.006):
            out.append(("zr[%s] eps%+.4f" % (name, eps),
                        _damaged_capture(data, eps, 560.0, nd), data,
                        "zerorun"))

    # ---- weakbits: > 5 weak bits (the v2.2 R7 class) ----------------
    for eps in (0.0015, 0.002, 0.0025, 0.003, 0.004, 0.005, 0.006,
                0.008, 0.012, -0.03, -0.045, -0.06):
        for t0 in (470.0, 650.0):
            name, data = pay[next(rnd) % len(pay)]
            out.append(("weak eps%+.4f t0=%.0f/%s" % (eps, t0, name),
                        _damaged_capture(data, eps, t0, nd), data,
                        "weakbits"))

    # ---- drift: within-capture linear eps ramp ----------------------
    for dr in (-0.004, -0.002, 0.002, 0.004):
        for eps in (-0.011, -0.002):
            name, data = pay[next(rnd) % len(pay)]
            out.append(("drift%+.3f eps%+.3f/%s" % (dr, eps, name),
                        _damaged_capture(data, eps, 560.0, nd, drift=dr),
                        data, "drift"))
    return out


def report(nd, ev=None):
    if ev is None:
        ev = L.load_ref()
    ev._configure(nd, chk=6)
    cs = cases(nd)
    agg = collections.defaultdict(lambda: [0, 0, 0])
    causes = collections.Counter()
    wrong = []
    for (tag, raw, truth, cls) in cs:
        out, info = ev.decode_ex(L.linearize(raw))
        em = out is not None
        ok = em and out == truth
        agg[cls][0] += 1
        agg[cls][1] += int(em)
        agg[cls][2] += int(em and not ok)
        causes[info["cause"] or ("ok" if ok else "WRONG")] += 1
        if em and not ok:
            wrong.append((tag, cls, out.hex(), truth.hex()))
    print("== fuzz_v23 ND=%d : %d cases ==" % (nd, len(cs)))
    print("%-11s %6s %9s %8s %8s" % ("class", "cases", "emitted",
                                     "correct", "WRONG"))
    tn = te = tw = 0
    for k in sorted(agg):
        n, em, wr = agg[k]
        tn += n
        te += em
        tw += wr
        print("%-11s %6d %9d %8d %8d" % (k, n, em, em - wr, wr))
    print("%-11s %6d %9d %8d %8d   -> wrong/emission = %.4f %%"
          % ("TOTAL", tn, te, te - tw, tw, 100.0 * tw / te if te else 0.0))
    print("causes:", dict(causes.most_common()))
    for w in wrong:
        print("  WRONG", w[0], w[1])
        print("     got  ", w[2])
        print("     truth", w[3])
    return tn, te, tw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    ev = L.load_ref()
    tot = [0, 0, 0]
    for nd in (16, 48):
        if a.report:
            r = report(nd, ev)
            tot = [x + y for x, y in zip(tot, r)]
        else:
            print("ND=%d: %d cases" % (nd, len(cases(nd))))
    if a.report:
        print("\nBOTH GEOMETRIES: %d cases, %d emitted, %d WRONG "
              "-> %.4f %% of emissions"
              % (tot[0], tot[1], tot[2],
                 100.0 * tot[2] / tot[1] if tot[1] else 0.0))


if __name__ == "__main__":
    main()
