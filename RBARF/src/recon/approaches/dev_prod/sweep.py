#!/usr/bin/env python3
"""Delivery-vs-(eps, t0) sweep of the REAL production decoder (decode.c,
gcc host build, ND48/CHK4) over synthetic captures from the calibrated
sampler model, for the 10 gate payloads. Writes sweep_results.jsonl."""
import json
import multiprocessing as mp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sweeplib as S


def eps_grid():
    pts = set()
    e = -0.036
    while e <= 0.0401:
        pts.add(round(e, 5))
        e += 0.001
    e = -0.005
    while e <= 0.0201:
        pts.add(round(e, 5))
        e += 0.0005
    e = -0.002
    while e <= 0.0060:
        pts.add(round(e, 5))
        e += 0.0002
    return sorted(pts)


T0S = [254.0 + i * (501.0 - 254.0) / 15 for i in range(16)]


def work(job):
    name, data_hex, eps, t0 = job
    r = S.run_case(bytes.fromhex(data_hex), eps, t0)
    r["pattern"] = name
    return r


def main():
    jobs = []
    for name, data in S.FRAMES:
        for eps in eps_grid():
            for t0 in T0S:
                jobs.append((name, data.hex(), eps, t0))
    print(f"{len(jobs)} cases ({len(eps_grid())} eps x {len(T0S)} t0 x 10)")
    out = Path(__file__).parent / "sweep_results.jsonl"
    with mp.Pool(20) as pool, open(out, "w") as f:
        for i, r in enumerate(pool.imap_unordered(work, jobs, chunksize=64)):
            f.write(json.dumps(r) + "\n")
            if (i + 1) % 2000 == 0:
                print(f"  {i+1}/{len(jobs)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
