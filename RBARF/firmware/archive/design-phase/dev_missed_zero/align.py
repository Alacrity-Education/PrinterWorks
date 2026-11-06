import sys, cmath, math
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
        E.append(b*BIT)
        E.append(b*BIT+(700.0 if bit else 350.0))
    return E

def observed(s):
    """list of (n_before, n_after) brackets for each transition, alternating starting with rise"""
    O=[]
    lev=[v for _,_,v in s]
    assert lev[0]==1
    O.append((-1,0))   # initial rise before sample 0
    for n in range(1,len(lev)):
        if lev[n]!=lev[n-1]:
            O.append((n-1,n))
    return O

def align(O,E,tlin):
    NO=len(O); NE=len(E)
    INF=float('inf')
    # dp[j][m] : matched observed j..(first j) to expected up to m
    # iterate j from 0..NO-1, m same parity as j
    DEL=250.0
    dp=[[INF]*(NE+1) for _ in range(NO+1)]
    bk=[[None]*(NE+1) for _ in range(NO+1)]
    dp[0][0]=0.0
    for j in range(NO+1):
        for m in range(NE+1):
            cur=dp[j][m]
            if cur==INF: continue
            # delete pair of expected (m,m+1)
            if m+2<=NE:
                v=cur+DEL
                if v<dp[j][m+2]: dp[j][m+2]=v; bk[j][m+2]=(j,m,'D')
            if j<NO and m<NE:
                c=abs(tlin(O[j])-E[m])
                v=cur+c
                if v<dp[j+1][m+1]: dp[j+1][m+1]=v; bk[j+1][m+1]=(j,m,'M')
    best=None
    for m in range(NE+1):
        if dp[NO][m]<INF and (best is None or dp[NO][m]<best[0]): best=(dp[NO][m],m)
    # backtrack
    pairs=[]
    j,m=NO,best[1]
    while (j,m)!=(0,0):
        pj,pm,op=bk[j][m]
        if op=='M': pairs.append((pj,pm))
        j,m=pj,pm
    pairs.reverse()
    return best[0],pairs

for pat in ['aa','zeros','ones','rnd1']:
    c=[x for x in caps if x['pattern']==pat and x['rep']==0][0]
    s=[x for x in linearize(c['capture']) if x[0]<100]
    O=observed(s); E=expected_edges(c)
    P=2497.5
    def tlin(br):
        n=br[1]
        it,sl=s[n][0],s[n][1]
        return it*P+G[sl]*P/40.0 - 156.0
    cost,pairs=align(O,E,tlin)
    print(pat,'obs',len(O),'exp',len(E),'matched',len(pairs),'cost',round(cost))
    # residuals: t(n_after) >= E[m], t(n_before)<=E[m]
    res=[]
    for j,m in pairs:
        nb,na=O[j]
        n=na
        it,sl=s[n][0],s[n][1]
        idx=it*8+sl
        res.append((idx,it,sl,E[m]-(it*P+G[sl]*P/40.0)))
    for r in res[::7]:
        print('   idx%4d it%3d sl%d  resid %8.1f'%r)
