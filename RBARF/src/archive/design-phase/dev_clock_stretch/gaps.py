"""Measure real inter-slot gaps from captures that already decode exactly."""
import sys, importlib.util
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize, score

spec = importlib.util.spec_from_file_location(
    'cs', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

BIT = 1250.0


def main():
    meta, caps = load_dataset()
    # accumulate absolute-time estimates per sample and derive gaps
    acc = [[] for _ in range(8)]        # gap after slot s, in ns/bit units
    for c in caps:
        if c['rep'] == 2:
            continue
        s = linearize(c['capture'])
        fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
        sc, llr, C, rate = cs._solve(s)
        bits = cs._bits_from(llr)
        if bits != fb:
            continue
        cyc = cs._cycles(s)
        # absolute time of each sample: k*1250 + phase
        k = 0
        times = {}
        i = 0
        while i < len(s) and cyc[i] < C[0]:
            i += 1
        while i < len(s) and k < cs.NBITS:
            if cyc[i] >= C[k + 1]:
                k += 1
                continue
            span = C[k + 1] - C[k]
            t = k * BIT + (cyc[i] - C[k]) * BIT / span
            times[(s[i][0], s[i][1])] = (t, span)
            i += 1
        # gaps
        for (it, sl), (t, span) in times.items():
            nxt = (it, sl + 1) if sl < 7 else (it + 1, 0)
            if nxt in times:
                t2 = times[nxt][0]
                # convert ns -> cycles using local rate: span cycles per bit
                cycles = (t2 - t) / BIT * span
                acc[sl].append(cycles)
    print("gap-after-slot (cycles), median / mean / n:")
    tot = 0.0
    for sl in range(8):
        v = sorted(acc[sl])
        if not v:
            print(sl, "none")
            continue
        med = v[len(v) // 2]
        mean = sum(v) / len(v)
        tot += med
        print(f"  slot {sl}: med={med:6.3f} mean={mean:6.3f} n={len(v)} "
              f"p10={v[len(v)//10]:.2f} p90={v[9*len(v)//10]:.2f}")
    print("sum of medians (loop cycles):", round(tot, 3))
    # cumulative positions
    pos = [0.0]
    for sl in range(7):
        v = sorted(acc[sl])
        pos.append(pos[-1] + v[len(v) // 2])
    print("positions rel slot0:", [round(x, 3) for x in pos])


main()
