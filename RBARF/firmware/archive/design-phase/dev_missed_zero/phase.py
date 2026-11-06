import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
for pat,W in [('ones',700.0),('zeros',350.0)]:
  for rep in (0,1,2):
    c=[x for x in caps if x['pattern']==pat and x['rep']==rep][0]
    s=[x for x in linearize(c['capture']) if 18<=x[0]<=76]  # payload region only
    best=None
    P=2480.0
    while P<=2530.0:
        tot=0; phis=[]
        for k in range(8):
            ss=[(i,v) for i,sl,v in s if sl==k]
            bb=None
            for ph10 in range(0,1250,5):
                m=0
                for i,v in ss:
                    ph=(ph10+i*(P-2500.0))%BIT
                    pv=1 if ph<W else 0
                    if pv!=v: m+=1
                if bb is None or m<bb[0]: bb=(m,ph10)
            tot+=bb[0]; phis.append(bb[1])
        if best is None or tot<best[0]: best=(tot,P,phis)
        P+=0.5
    print(pat,rep,'viol',best[0],'P',best[1],'phis',best[2])
