import sys
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

meta, caps = load_dataset()
want = sys.argv[1] if len(sys.argv) > 1 else 'ones'
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 0
for c in caps:
    if c['pattern'] == want and c['rep'] == rep:
        s = linearize(c['capture'])
        bits = [int(b) for byte in bytes.fromhex(c['frame']) for b in f"{byte:08b}"]
        print('frame bits:', ''.join(map(str, bits)))
        lv = ''.join(str(v) for _, _, v in s)
        # trim to end of frame region
        last1 = lv.rfind('1')
        lv = lv[:last1 + 1]
        print('nsamp', len(lv))
        # run lengths
        runs = []
        cur = lv[0]; n = 1
        for ch in lv[1:]:
            if ch == cur:
                n += 1
            else:
                runs.append((cur, n)); cur = ch; n = 1
        runs.append((cur, n))
        print('runs:', ' '.join(f"{c_}{n_}" for c_, n_ in runs))
        # per-slot index of each sample
        print('slots at run starts:')
        idx = 0
        out = []
        for c_, n_ in runs:
            out.append(f"{c_}{n_}@s{s[idx][1]}i{s[idx][0]}")
            idx += n_
        print(' '.join(out))
        break
