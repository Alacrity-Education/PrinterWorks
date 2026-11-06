import sys, math, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
G=[1,5,9,13,17,21,27,32]
DS=[]
for c in caps:
    s=[x for x in linearize(c['capture']) if x[0]<100]
    lev=[v for _,_,v in s]
    rises=[]; falls=[]
    for n in range(1,len(lev)):
        if lev[n] and not lev[n-1]: rises.append((s[n-1][0],s[n-1][1],s[n][0],s[n][1]))
        elif lev[n-1] and not lev[n]: falls.append((s[n-1][0],s[n-1][1],s[n][0],s[n][1]))
    DS.append(dict(c=c,rises=rises,falls=falls))

def cost_rise(rises,P,a,cap=300.0):
    tot=0.0
    for ib,sb,ia,sa in rises:
        lo=P*(ib+a[sb]); hi=P*(ia+a[sa])
        # nearest multiple of BIT to interval
        b=round(((lo+hi)/2)/BIT)
        e=b*BIT
        d=(lo-e) if e<lo else ((e-hi) if e>hi else 0.0)
        tot+=min(d,cap)
    return tot
def cost_fall(falls,P,a,cap=300.0):
    tot=0.0
    for ib,sb,ia,sa in falls:
        lo=P*(ib+a[sb]); hi=P*(ia+a[sa])
        mid=(lo+hi)/2
        b=math.floor(mid/BIT)
        best=1e18
        for bb in (b-1,b,b+1):
            for w in (350.0,700.0):
                e=bb*BIT+w
                d=(lo-e) if e<lo else ((e-hi) if e>hi else 0.0)
                best=min(best,d)
        tot+=min(best,cap)
    return tot

a=[g/40.0 for g in G]
Ps=[2499.0]*len(DS)
def fitP(d,a,P0):
    best=None
    for st in (4.0,1.0,0.25,0.05,0.01):
        base=P0 if best is None else best[1]
        for i in range(-12,13):
            cand=base+i*st
            if not(2470<cand<2540): continue
            v=cost_rise(d['rises'],cand,a)+cost_fall(d['falls'],cand,a)
            if best is None or v<best[0]: best=(v,cand)
    return best[1]
for rnd in range(6):
    Ps=[fitP(d,a,P) for d,P in zip(DS,Ps)]
    for k in range(8):
        lo = a[k-1]+0.005 if k>0 else 0.0
        hi = a[k+1]-0.005 if k<7 else 1.0
        best=None
        i=lo
        while i<hi:
            aa=list(a); aa[k]=i
            v=sum(cost_rise(d['rises'],P,aa)+cost_fall(d['falls'],P,aa) for d,P in zip(DS,Ps))
            if best is None or v<best[0]: best=(v,i)
            i+=0.002
        a[k]=best[1]
    tot=sum(cost_rise(d['rises'],P,a)+cost_fall(d['falls'],P,a) for d,P in zip(DS,Ps))
    print('rnd',rnd,'cost',round(tot),'P',round(min(Ps),2),round(max(Ps),2))
    print('   cycles',[round(x*40,2) for x in a])
json.dump({'a':a,'Ps':Ps,'pat':[d['c']['pattern']+str(d['c']['rep']) for d in DS]},open('approaches/dev_missed_zero/fit8.json','w'))
