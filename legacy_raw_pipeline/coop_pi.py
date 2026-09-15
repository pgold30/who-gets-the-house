"""pi for co-operatives, using the recovered UCC financing flag."""
import json, collections, datetime as dt, numpy as np
rng=np.random.default_rng(20260903); MIN_HOLD=int(36*30.44)
rows=json.load(open("coop_rows2.json"))
print(f"co-op sales classified: {len(rows):,}")
def q(d): return (d.year-2016)*4+(d.month-1)//3
def build(rs,min_hold=MIN_HOLD,boro=None):
    by=collections.defaultdict(list)
    for r in rs:
        if boro and r["borough"]!=boro: continue
        by[r["unit"]].append(r)
    out=[]
    for u,g in by.items():
        g=sorted(g,key=lambda r:r["date"])
        for a,z in zip(g,g[1:]):
            da,dz=dt.date.fromisoformat(a["date"]),dt.date.fromisoformat(z["date"])
            if (dz-da).days>=min_hold: out.append((a,z,da,dz))
    return out
def excess(P):
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
    beta,*_=np.linalg.lstsq(X,y,rcond=None); return y-X@beta
def pisym(P,res):
    k=np.array([f"{'c' if not int(a['financed_base']) else 'f'}{'c' if not int(z['financed_base']) else 'f'}"
                for a,z,da,dz in P])
    A,B=res[k=="cf"],res[k=="fc"]
    if len(A)<40 or len(B)<40: return None
    return (A.mean()-B.mean())/2, len(A)+len(B), A.mean()+B.mean()
def boot(P,R=300):
    bb=np.array([a["unit"] for a,z,da,dz in P]); u=np.unique(bb)
    ix={x:np.where(bb==x)[0] for x in u}; out=[]
    for _ in range(R):
        s=rng.choice(u,size=len(u),replace=True)
        Pb=[P[i] for i in np.concatenate([ix[x] for x in s])]
        try:
            v=pisym(Pb,excess(Pb))
            if v: out.append(v[0])
        except Exception: pass
    return np.percentile(out,[2.5,97.5]) if len(out)>25 else (np.nan,np.nan)

print("="*90); print("CO-OPERATIVES: pi by holding filter"); print("="*90)
print(f"{'min hold':<12} {'pairs':>7} {'switch':>7} {'pi':>9} {'95% CI':>20} {'asym':>9}")
out={}
for months in [12,24,36,48,60]:
    P=build(rows,int(months*30.44))
    v=pisym(P,excess(P)) if len(P)>300 else None
    if v:
        ci=boot(P) if months==36 else (np.nan,np.nan)
        out[months]=dict(pi=float(v[0]),pairs=len(P),switch=v[1],asym=float(v[2]),
                         ci=[float(ci[0]),float(ci[1])])
        cis=f"[{ci[0]:8.4f},{ci[1]:7.4f}]" if not np.isnan(ci[0]) else " "*20
        print(f"{'>= '+str(months)+'m':<12} {len(P):7,} {v[1]:7,} {v[0]:9.4f} {cis} {v[2]:+9.4f}")
    else:
        print(f"{'>= '+str(months)+'m':<12} {len(P):7,}   too few switchers")
print()
print("="*90); print("BY BOROUGH (36-month filter)"); print("="*90)
BORO={"1":"Manhattan","2":"Bronx","3":"Brooklyn","4":"Queens","5":"Staten Island"}
for b,name in BORO.items():
    P=build(rows,boro=b)
    v=pisym(P,excess(P)) if len(P)>300 else None
    if v:
        ci=boot(P,200)
        out[name]=dict(pi=float(v[0]),pairs=len(P),switch=v[1],ci=[float(ci[0]),float(ci[1])])
        print(f"{name:<16} {len(P):7,} {v[1]:7,} {v[0]:9.4f} [{ci[0]:8.4f},{ci[1]:7.4f}]")
    else:
        print(f"{name:<16} {len(P):7,}   too few")
json.dump(out,open("coop_pi_results.json","w"),indent=1)
print("\nwrote coop_pi_results.json")
