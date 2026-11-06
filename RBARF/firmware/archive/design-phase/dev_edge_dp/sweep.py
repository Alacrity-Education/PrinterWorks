import sys
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from run import run

CONFIGS = eval(sys.argv[1]) if len(sys.argv) > 1 else [{}]
for cfg in CONFIGS:
    print('CFG', cfg)
    run(cfg, verbose=False)
    sys.stdout.flush()
