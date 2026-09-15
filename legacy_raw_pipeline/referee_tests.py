"""Adversarial robustness for the house / condominium result and the estimator.

Five attacks a referee would make, and the tests that answer them.

  A. The house-condominium difference is a PRICE difference, not a type
     difference. Condominiums and houses transact at different price levels, and
     if pi varies with price the comparison confounds the two.
  B. The repeat-sales index is fitted on the same pairs used for the test, so it
     could absorb the treatment. Refit on non-switching pairs only and score the
     switchers out of sample.
  C. Delayed financing. A cash purchase refinanced soon after would be recorded
     as cash here. How much of the "cash" category acquires a mortgage later?
  D. Selection into repeat sales, and into the matched condominium subsample.
  E. The symmetry test assumes improvement runs cash-then-financed. Do the two
     switching directions differ in ways consistent with that?
"""
import gzip, csv, json, collections, datetime as dt, numpy as np
rng = np.random.default_rng(20260903)
MIN_HOLD = int(36*30.44)

rows=[]
with gzip.open("panel2.csv.gz","rt",newline="") as fh:
    for r in csv.DictReader(fh): rows.append(r)

def q(d): return (d.year-2016)*4+(d.month-1)//3

def build(rs, min_hold=MIN_HOLD, **f):
    by=collections.defaultdict(list)
    for r in rs:
        if any(r[k]!=v for k,v in f.items()): continue
        by[r["bbl"]].append(r)
    out=[]
    for b,g in by.items():
        g=sorted(g,key=lambda r:r["date"])
        for a,z in zip(g,g[1:]):
            da,dz=dt.date.fromisoformat(a["date"]),dt.date.fromisoformat(z["date"])
            if (dz-da).days>=min_hold: out.append((a,z,da,dz))
    return out

def design(P):
    bs=sorted({a["borough"] for a,z,da,dz in P}); nq=max(q(dz) for a,z,da,dz in P)+1
    cols,j={},0
    for b in bs:
        for t in range(1,nq): cols[(b,t)]=j; j+=1
    X=np.zeros((len(P),j))
    y=np.array([np.log(float(z["price"]))-np.log(float(a["price"])) for a,z,da,dz in P])
    for i,(a,z,da,dz) in enumerate(P):
        b=a["borough"]
        if (b,q(da)) in cols: X[i,cols[(b,q(da))]]-=1
        if (b,q(dz)) in cols: X[i,cols[(b,q(dz))]]+=1
    return y,X,cols

def excess(P):
    y,X,_=design(P); beta,*_=np.linalg.lstsq(X,y,rcond=None); return y-X@beta

def kinds(P):
    return np.array([f"{'c' if 1-int(a['financed_base']) else 'f'}"
                     f"{'c' if 1-int(z['financed_base']) else 'f'}" for a,z,da,dz in P])

def pisym(P,res):
    k=kinds(P); A,B=res[k=="cf"],res[k=="fc"]
    if len(A)<40 or len(B)<40: return None
    return (A.mean()-B.mean())/2, len(A)+len(B), A.mean()+B.mean()

def boot(P,R=250):
    bb=np.array([a["bbl"] for a,z,da,dz in P]); u=np.unique(bb)
    ix={x:np.where(bb==x)[0] for x in u}; out=[]
    for _ in range(R):
        s=rng.choice(u,size=len(u),replace=True)
        Pb=[P[i] for i in np.concatenate([ix[x] for x in s])]
        try:
            v=pisym(Pb,excess(Pb))
            if v: out.append(v[0])
        except Exception: pass
    return np.percentile(out,[2.5,97.5]) if len(out)>25 else (np.nan,np.nan)

res={}
# ---------- A. price levels ----------
print("="*92); print("A.  IS IT PRICE, NOT PROPERTY TYPE?"); print("="*92)
ph=np.array([float(r["price"]) for r in rows if r["src"]=="house"])
pc=np.array([float(r["price"]) for r in rows if r["src"]=="condo"])
print(f"   house  price  median {np.median(ph):>10,.0f}   p25 {np.percentile(ph,25):>10,.0f}  p75 {np.percentile(ph,75):>10,.0f}")
print(f"   condo  price  median {np.median(pc):>10,.0f}   p25 {np.percentile(pc,25):>10,.0f}  p75 {np.percentile(pc,75):>10,.0f}")
lo,hi=max(np.percentile(ph,10),np.percentile(pc,10)), min(np.percentile(ph,90),np.percentile(pc,90))
print(f"\n   common-support price band: {lo:,.0f} to {hi:,.0f}")
band=[r for r in rows if lo<=float(r["price"])<=hi]
print(f"   sales in band: {len(band):,}  (houses {sum(1 for r in band if r['src']=='house'):,}, "
      f"condos {sum(1 for r in band if r['src']=='condo'):,})")
print(f"\n{'specification':<34} {'pairs':>7} {'switch':>7} {'pi':>8} {'95% CI':>20}")
for lab,rs_,f in [("houses, common band", band, {"src":"house"}),
                  ("condos, common band", band, {"src":"condo"})]:
    P=build(rs_,**f)
    v=pisym(P,excess(P)) if len(P)>300 else None
    if v:
        ci=boot(P); res[lab]=dict(pi=float(v[0]),ci=[float(ci[0]),float(ci[1])],pairs=len(P),switch=v[1])
        print(f"{lab:<34} {len(P):7,} {v[1]:7,} {v[0]:8.4f} [{ci[0]:8.4f},{ci[1]:7.4f}]")
    else: print(f"{lab:<34} {len(P):7,}   too few")
# pi by price tercile within type
print(f"\n{'pi by price tercile within type':<34}")
for src in ["house","condo"]:
    p=np.array([float(r["price"]) for r in rows if r["src"]==src])
    cuts=np.percentile(p,[33.3,66.7])
    for ti,(a_,b_) in enumerate([(0,cuts[0]),(cuts[0],cuts[1]),(cuts[1],1e12)]):
        sub=[r for r in rows if r["src"]==src and a_<=float(r["price"])<b_]
        P=build(sub)
        v=pisym(P,excess(P)) if len(P)>300 else None
        lab=f"   {src} tercile {ti+1} ({a_/1e3:,.0f}k-{min(b_,6e6)/1e3:,.0f}k)"
        if v:
            res[lab.strip()]=dict(pi=float(v[0]),pairs=len(P),switch=v[1])
            print(f"{lab:<44} {len(P):6,} {v[1]:6,} {v[0]:8.4f}")
        else: print(f"{lab:<44} {len(P):6,}   too few")
json.dump(res,open("referee_A.json","w"),indent=1)
