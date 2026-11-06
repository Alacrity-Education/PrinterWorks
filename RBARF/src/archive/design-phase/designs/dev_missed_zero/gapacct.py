"""Prototype: pulse -> bit-grid assignment + gap accounting.

For each observed high run:
  rise bracket = (t[last low before], t[first high])   -> true rise inside
  fall bracket = (t[last high],      t[first low after]) -> true fall inside
Assign n = round(rise_mid / BIT); width class from fall_mid.
Then every bit index not covered by a run is a swallowed 0.
"""
from common import *
import numpy as np, json
from collections import Counter

OFF=np.array(SLOT_OFF); H0,H1=375.0,750.0

def fit_best(it,sl,lv,bits,slo=0.995,shi=1.010):
    bn=np.array(bits,np.int8); nb=len(bits)
    pos=it*LOOP_NOM+OFF[sl]
    T0=np.arange(-100.0,400.0,5.0)
    def scan(scales,t0s):
        best=None
        for scale in scales:
            base=scale*pos
            t=base[None,:]+t0s[:,None]
            k=np.floor(t/BIT).astype(np.int64); ok=(k>=0)&(k<nb); kc=np.clip(k,0,nb-1)
            hi=np.where(bn[kc]==1,H1,H0)
            pred=(((t-k*BIT)<hi)&ok)
            a=(pred==lv[None,:]).sum(axis=1)
            j=int(a.argmax())
            if best is None or a[j]>best[0]: best=(int(a[j]),float(scale),float(t0s[j]))
        return best
    b=scan(np.linspace(slo,shi,376),T0)
    b=scan(np.linspace(b[1]-4e-5,b[1]+4e-5,41),np.arange(b[2]-6,b[2]+6.1,1.0))
    return b

def pulses(t,lv):
    """[(i0,i1)] index ranges of high runs."""
    out=[];i=0;n=len(lv)
    while i<n:
        if lv[i]:
            j=i
            while j+1<n and lv[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out

def analyze(c, verbose=False):
    s=linearize(c['capture']); bits=bits_of(bytes.fromhex(c['frame']))
    it=np.array([i for i,_,_ in s],float); sl=np.array([x for _,x,_ in s]); lv=np.array([v for _,_,v in s],bool)
    ag,scale,t0=fit_best(it,sl,lv,bits)
    t=t0+scale*(it*LOOP_NOM+OFF[sl])
    P=pulses(t,lv)
    P=[p for p in P if t[p[0]]<193*BIT]
    recs=[]
    for i0,i1 in P:
        ra=t[i0-1] if i0>0 else t[i0]-250.0
        rb=t[i0]
        fa=t[i1]
        fb=t[i1+1] if i1+1<len(t) else t[i1]+250.0
        rmid=(ra+rb)/2; fmid=(fa+fb)/2
        n=int(round(rmid/BIT))
        recs.append(dict(i0=i0,i1=i1,ra=ra,rb=rb,fa=fa,fb=fb,rmid=rmid,fmid=fmid,
                         n=n,nsamp=i1-i0+1,width=fmid-rmid))
    return dict(cap=c,bits=bits,scale=scale,t0=t0,agree=ag,t=t,lv=lv,recs=recs,sl=sl,it=it)

meta,caps=load()
res_res=[]   # rise residuals
span_stats=Counter(); nerr=Counter(); wid_by_span=Counter()
tot=Counter()
out=[]
for c in caps:
    A=analyze(c); bits=A['bits']; recs=A['recs']
    covered=set()
    ns=[r['n'] for r in recs]
    # true span of each pulse: which bits does it really cover?
    for r in recs:
        res_res.append(r['rmid']/BIT - r['n'])
    # duplicates / non-monotonic
    dup=len(ns)-len(set(ns))
    mono=all(b>a for a,b in zip(ns,ns[1:]))
    # gap accounting: number of hidden bits between consecutive pulses
    # span estimate from width
    for r in recs:
        # candidate spans: 1 bit (h=375 or 750), 2 bits merged, 3 bits
        best=None
        for span in (1,2,3):
            for lastb in (0,1):
                # end bit index = n+span-1 ; fall at (n+span-1)*BIT + h
                h=H1 if lastb else H0
                pred=(r['n']+span-1)*BIT+h
                d=abs(pred-r['fmid'])
                if best is None or d<best[0]: best=(d,span,lastb)
            
        r['span']=best[1]; r['lastb']=best[2]; r['ferr']=best[0]
        span_stats[best[1]]+=1
        wid_by_span[(best[1],best[2],round(r['width']/125)*125)]+=1
    # truth: assign each true bit to the pulse that contains its high
    truth_cov={}
    for k in range(len(bits)):
        h=H1 if bits[k] else H0
        lo,hi=k*BIT,k*BIT+h
        for ri,r in enumerate(recs):
            if r['rmid']<hi and r['fmid']>lo: truth_cov.setdefault(k,ri)
    S=[k for k in range(len(bits)) if k not in truth_cov]
    truespan=Counter()
    for ri,r in enumerate(recs):
        ks=[k for k,v in truth_cov.items() if v==ri]
        r['truespan']=len(ks); r['truen']=min(ks) if ks else None
        truespan[len(ks)]+=1
    nb_ok=sum(1 for r in recs if r['truen'] is not None and r['n']==r['truen'])
    sp_ok=sum(1 for r in recs if r['truespan']==r['span'])
    tot['pulses']+=len(recs); tot['n_ok']+=nb_ok; tot['span_ok']+=sp_ok
    tot['swallowed']+=len(S); tot['merged']+=sum(v-1 for k,v in truespan.items() if k>1 for v in [k])
    out.append(dict(pattern=c['pattern'],rep=c['rep'],agree=A['agree'],loop=A['scale']*2500,
                    t0=A['t0'],npulse=len(recs),swallowed=len(S),
                    truespan=dict(truespan),n_ok=nb_ok,span_ok=sp_ok,dup=dup,mono=mono,
                    swal_bits=S))
    print(f"{c['pattern']:11s} {c['rep']} loop={A['scale']*2500:7.2f} ag={A['agree']:4d} "
          f"pulses={len(recs):3d} swallow={len(S):3d} truespan={dict(sorted(truespan.items()))} "
          f"n_ok={nb_ok:3d} span_ok={sp_ok:3d} dup={dup} mono={mono}")
r=np.array(res_res)
print("\nrise-residual (rmid/BIT - n): mean %.4f std %.4f max|.| %.4f"%(r.mean(),r.std(),np.abs(r).max()))
print("index-assignment accuracy: %d/%d"%(tot['n_ok'],tot['pulses']))
print("span-classification accuracy: %d/%d"%(tot['span_ok'],tot['pulses']))
print("total swallowed bits:",tot['swallowed'])
json.dump(out,open('gapacct.json','w'),indent=1)
