import sys, math, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
G=[1,5,9,13,17,21,27,32]
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
def expected_edges(c):
    E=[]
    for b,bit in enumerate(fb(c)):
        E.append(b*BIT); E.append(b*BIT+(700.0 if bit else 350.0))
    return E
DS=[]
for c in caps:
    s=[x for x in linearize(c['capture']) if x[0]<100]
    lev=[v for _,_,v in s]
    O=[(-1,0)]
    for n in range(1,len(lev)):
        if lev[n]!=lev[n-1]: O.append((n-1,n))
    # brackets as (it_b, sl_b, it_a, sl_a)
    br=[]
    for nb,na in O:
        if nb<0: b=(None,None)
        else: b=(s[nb][0],s[nb][1])
        aa=(s[na][0],s[na][1]) if na<len(s) else (None,None)
        br.append((b[0],b[1],aa[0],aa[1]))
    DS.append(dict(c=c,br=br,E=expected_edges(c),n=len(s)))

def bounds(b,P,a):
    ib,sb,ia,sa=b
    lo=-1e9 if ib is None else P*(ib+a[sb])
    hi=1e9 if ia is None else P*(ia+a[sa])
    return lo,hi

def hinge_pairs(d,pairs,P,a,only_slot=None):
    tot=0.0; E=d['E']; br=d['br']
    for j,m in pairs:
        b=br[j]
        if only_slot is not None and b[1]!=only_slot and b[3]!=only_slot: continue
        lo,hi=bounds(b,P,a); e=E[m]
        if e<lo: tot+=lo-e
        elif e>hi: tot+=e-hi
    return tot

def align(d,P,a,DEL=400.0,band=20):
    E=d['E']; br=d['br']; NO=len(br); NE=len(E)
    INF=float('inf')
    tm=[bounds(b,P,a) for b in br]
    dp=[[INF]*(NE+1) for _ in range(NO+1)]
    bk=[[None]*(NE+1) for _ in range(NO+1)]
    dp[0][0]=0.0
    for j in range(NO+1):
        m0=max(0,j-2); m1=min(NE,j+band)
        row=dp[j]
        for m in range(m0,m1+1):
            cur=row[m]
            if cur==INF: continue
            if m+2<=NE:
                v=cur+DEL
                if v<dp[j][m+2]: dp[j][m+2]=v; bk[j][m+2]=(j,m,'D')
            if j<NO and m<NE:
                lo,hi=tm[j]; e=E[m]
                c=(lo-e) if e<lo else ((e-hi) if e>hi else 0.0)
                v=cur+c
                if v<dp[j+1][m+1]: dp[j+1][m+1]=v; bk[j+1][m+1]=(j,m,'M')
    best=min(((dp[NO][m],m) for m in range(NE+1) if dp[NO][m]<INF))
    pairs=[]; j,m=NO,best[1]
    while (j,m)!=(0,0):
        pj,pm,op=bk[j][m]
        if op=='M': pairs.append((pj,pm))
        j,m=pj,pm
    pairs.reverse()
    return best[0],pairs

a=[g/40.0 for g in G]
Ps=[2499.0]*len(DS)
for rnd in range(8):
    tot=0; algn=[]
    for d,P in zip(DS,Ps):
        cst,pairs=align(d,P,a); algn.append(pairs); tot+=cst
    newPs=[]
    for d,P,pairs in zip(DS,Ps,algn):
        best=None
        for st in (2.0,0.4,0.08,0.02):
            base=P if best is None else best[1]
            for i in range(-15,16):
                cand=base+i*st
                v=hinge_pairs(d,pairs,cand,a)
                if best is None or v<best[0]: best=(v,cand)
        newPs.append(best[1])
    Ps=newPs
    for k in range(8):
        best=None
        for i in range(0,261):
            cand=i/260.0
            aa=list(a); aa[k]=cand
            v=sum(hinge_pairs(d,pairs,P,aa,only_slot=k) for d,P,pairs in zip(DS,Ps,algn))
            if best is None or v<best[0]: best=(v,cand)
        a[k]=best[1]
    ht=sum(hinge_pairs(d,pairs,P,a) for d,P,pairs in zip(DS,Ps,algn))
    print('rnd',rnd,'alcost',round(tot),'hinge',round(ht),'P',round(min(Ps),1),round(max(Ps),1))
    print('   cycles',[round(x*40,2) for x in a])
json.dump({'a':a,'Ps':Ps},open('approaches/dev_missed_zero/fit7.json','w'))
