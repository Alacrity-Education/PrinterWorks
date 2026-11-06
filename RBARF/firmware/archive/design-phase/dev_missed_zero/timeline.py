import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0;T0H=350.0;T1H=700.0;NB=192
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
STEP=25.0
def sig_pen(t,v,bits):
    b=int(t//BIT)
    if b<0: return (0.0 if v==0 else 200.0)
    if b>=NB: return (0.0 if v==0 else 200.0)
    W=T1H if bits[b] else T0H
    ph=t-b*BIT
    if ph<W: return 0.0 if v else ph
    return (min(ph-W,BIT-ph) if v else 0.0)
DOCGAP=[4,4,4,4,4,6,5,6]  # gap after slot k, cycles
def run(pat,rep,tau=62.5,band=2200.0,mu=0.9):
    c=[x for x in caps if x['pattern']==pat and x['rep']==rep][0]
    s=linearize(c['capture']); bits=fb(c)
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+8]
    N=len(work)
    lin=[n*(2500.0/8) for n in range(N)]
    states=[]
    for n in range(N):
        lo=lin[n]-band; hi=lin[n]+band
        if lo<-200: lo=-200.0
        states.append((lo,int((hi-lo)/STEP)+1))
    INF=float('inf')
    prev=[sig_pen(states[0][0]+j*STEP,work[0][2],bits)+0.5*abs(states[0][0]+j*STEP-30.0) for j in range(states[0][1])]
    back=[]
    for n in range(1,N):
        lo0,m0=states[n-1]; lo1,m1=states[n]
        gexp=DOCGAP[work[n-1][1]]*tau
        cur=[INF]*m1; bk=[0]*m1
        for j in range(m1):
            t=lo1+j*STEP
            bestv=INF;bestj=0
            # feasible predecessors: gap in [80, 900]
            jmin=int((t-900.0-lo0)/STEP); jmax=int((t-80.0-lo0)/STEP)
            if jmin<0: jmin=0
            if jmax>m0-1: jmax=m0-1
            for jp in range(jmin,jmax+1):
                g=t-(lo0+jp*STEP)
                v=prev[jp]+mu*abs(g-gexp)
                if v<bestv: bestv=v;bestj=jp
            if bestv==INF: continue
            cur[j]=bestv+sig_pen(t,work[n][2],bits)
            bk[j]=bestj
        prev=cur; back.append(bk)
    j=min(range(len(prev)),key=lambda x:prev[x])
    print(pat,rep,'DPcost',round(prev[j],1))
    path=[0]*N; path[N-1]=j
    for n in range(N-1,0,-1):
        j=back[n-1][j]; path[n-1]=j
    ts=[states[n][0]+path[n]*STEP for n in range(N)]
    # report per-iteration slot0 time and effective period
    print('  it: t(slot0)  loopgap  gaps within loop (ns)')
    for it in range(0,96,6):
        idx=[n for n in range(N) if work[n][0]==it]
        if len(idx)<8: continue
        g=[round(ts[idx[k+1]]-ts[idx[k]]) for k in range(7)]
        nxt=[n for n in range(N) if work[n][0]==it+1]
        lp=round(ts[nxt[0]]-ts[idx[0]]) if nxt else 0
        print(f"   {it:3d} {ts[idx[0]]:9.0f} {lp:6d}  {g}")
    return ts,work,bits
for p in sys.argv[1].split(','):
    run(p,0)
