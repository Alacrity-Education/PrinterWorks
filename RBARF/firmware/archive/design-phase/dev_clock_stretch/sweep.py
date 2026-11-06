import importlib.util, sys, itertools, os
SRC = os.environ.get('CS_SRC', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize, score

meta, caps = load_dataset()
TRAIN = [(c, linearize(c['capture'])) for c in caps if c['rep'] in (0, 1)]


def run(**kw):
    spec = importlib.util.spec_from_file_location(
        'cs', SRC)
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    for k, v in kw.items():
        setattr(cs, k, v)
    cs._rebuild()
    ex = 0
    acc = 0.0
    perr = 0
    for c, s in TRAIN:
        fb = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
        r = cs._solve(s)
        llr = r[1]
        for k in range(32, 160):
            if (1 if llr[k] > 0 else 0) != fb[k]:
                perr += 1
        out = bytearray()
        for i in range(16):
            v = 0
            for j in range(8):
                v = (v << 1) | (1 if llr[32 + i * 8 + j] > 0 else 0)
            out.append(v)
        e, a = score(bytes(out), bytes.fromhex(c['payload']))
        ex += e
        acc += a
    return ex, acc / 36, perr


if __name__ == '__main__':
    import json
    cfgs = json.loads(sys.argv[1])
    for cfg in cfgs:
        ex, acc, perr = run(**cfg)
        print(f"{cfg} -> exact={ex}/36 acc={acc:.3%} perr={perr}", flush=True)
