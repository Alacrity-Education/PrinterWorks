#!/usr/bin/env python3
"""Feature-toggle matrix for embedded_ref (in-memory mutation only)."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "embedded_ref", ROOT / "approaches" / "embedded_ref.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)

meta, caps = load_dataset()
DATA = [(f"{c['pattern']}_{c['rep']}", linearize(c["capture"]),
         bytes.fromhex(c["payload"]), c["rep"]) for c in caps]


def run(label):
    ex, miss = [], []
    nb_err = 0
    for name, s, expv, rep in DATA:
        d = er.decode(s, meta)
        if d == expv:
            ex.append(name)
        else:
            miss.append(name)
            if d is not None:
                nb_err += sum(1 for a, b in zip(d, expv) if a != b)
    ho = sum(1 for n, s, e, r in DATA if r == 2 and n in ex)
    print(f"{label:42s} all {len(ex):2d}/54  holdout {ho:2d}/18  "
          f"byte_err={nb_err}  miss={sorted(miss)}", flush=True)


run("as shipped (ST=1 V=1 F=1)")
er.VOTES = False
run("votes off")
er.SELF_TRAIN = False
run("votes+selftrain off")
er.FAM_OFFSETS = False
run("votes+selftrain+fam off")
er.VOTES = True
run("fam+selftrain off, votes on")
er.SELF_TRAIN = True
run("fam off")
er.FAM_OFFSETS = True
er.SELF_TRAIN = False
run("selftrain off")
er.SELF_TRAIN = True

print("\n-- vote sub-toggles --")
er.DEAD_VOTE_MIN = 99
run("dead vote off")
er.DEAD_VOTE_MIN = 3
er.KNIFE_PAIR_MIN = 10**6
run("knife vote off")
er.KNIFE_PAIR_MIN = 40

print("\n-- margin sweeps --")
for v in (2, 3, 4, 5, 6, 8):
    er.CONF_M = v
    run(f"CONF_M={v}")
er.CONF_M = 4
for v in (2, 3, 4, 5, 6):
    er.KNIFE_M = v
    run(f"KNIFE_M={v}")
er.KNIFE_M = 4
for v in (2, 3, 4, 6, 8):
    er.ST_M = v
    run(f"ST_M={v}")
er.ST_M = 4
for v in (4, 6, 8, 10):
    er.FAM_CLAMP = v
    run(f"FAM_CLAMP={v}")
er.FAM_CLAMP = 6
