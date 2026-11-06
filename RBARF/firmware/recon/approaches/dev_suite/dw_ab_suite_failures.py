"""Is `rain` (and the other Lever-B-only suite failures) a real DW regression
or phase/thermal luck?  Host A/B: DW_EN 0 vs 1, same payloads, arm sweep."""
import sys, json
from pathlib import Path
NI = Path('/home/alex.lucaci/Projects/RBARF/src')
sys.path.insert(0, str(NI/'recon/approaches/dev_prod')); sys.path.insert(0, str(NI/'bench'))
from v23lib import load_ref, capture, linearize, set_params
S = json.loads((NI/'recon/approaches/dev_suite/singleshot_leverb.json').read_text())
pay = {(r['family'], r['name']): bytes.fromhex(r['data']) for r in S['suite']}
targets = [('demo','rain'), ('val-ext','vgray'), ('val-ext','vrnd4'), ('val-ext','vrnd7'),
           ('val-ext','vchecker'), ('demo','deepsea'), ('demo','duotone'),
           ('klipper','rnd_colors1'), ('klipper','rnd_colors2'), ('klipper','all_ff_base'),
           ('prod','rnd'), ('main-ext','p55'), ('main-ext','impulse_lo')]
ev = load_ref(); ev._configure(48, check=True, chk=6)
assert hasattr(ev, 'DW_EN'), [a for a in dir(ev) if 'DW' in a]
T0S = [70 + i*(658-70)/47 for i in range(48)]
EPSS = (-0.0080, -0.0090, -0.0105)
print(f"{'payload':22s} {'DW=0':>7s} {'DW=1':>7s}  delta   (n={len(T0S)*len(EPSS)} per column)")
tot0=tot1=0
for key in targets:
    data = pay[key]; acc={}
    for dw in (0,1):
        set_params(ev, DW_EN=dw); ok=0
        for eps in EPSS:
            for t0 in T0S:
                out,_ = ev.decode_ex(linearize(capture(data, eps, t0)))
                ok += (out == data)
        acc[dw]=ok
    tot0+=acc[0]; tot1+=acc[1]
    flag = "  <-- worse with DW" if acc[1] < acc[0] else ""
    print(f"{key[0]+'/'+key[1]:22s} {acc[0]:7d} {acc[1]:7d}  {acc[1]-acc[0]:+5d}{flag}")
print(f"{'TOTAL':22s} {tot0:7d} {tot1:7d}  {tot1-tot0:+5d}")
