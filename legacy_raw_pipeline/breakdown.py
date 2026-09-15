"""Where does the premium live? Borough x property type, plus a distress check."""
import json, gzip, csv, collections, numpy as np, datetime as dt
MIN_HOLD, BREAKEVEN = int(36*30.44), 0.117
PS_LO, PS_HI = 0.0374, 0.0781
rng = np.random.default_rng(20260903)
BORO = {"1":"Manhattan","2":"Bronx","3":"Brooklyn","4":"Queens","5":"Staten Island"}

rows=[]
with gzip.open("panel2.csv.gz","rt",newline="") as fh:
    for r in csv.DictReader(fh): rows.append(r)

def q(d): return (d.year-2016)*4+(d.month-1)//3

def build(rs, boro=None, src=None, drop_low=None):
    if drop_low:
        # distress proxy: drop the cheapest `drop_low` fraction within borough x year
        key=collections.defaultdict(list)
        for r in rs: key[(r["borough"], r["date"][:4])].append(float(r["price"]))
        cut={k:np.quantile(v,drop_low) for k,v in key.items() if len(v)>50}
        rs=[r for r in rs if float(r["price"])>=cut.get((r["borough"],r["date"][:4]),0)]
    by=collections.defaultdict(list)
    for r in rs:
        if boro and r["borough"]!=boro: continue
        if src and r["src"]!=src: continue
        by[r["bbl"]].append(r)
    out=[]
    for b,g in by.items():
        g=sorted(g,key=lambda r:r["date"])
        for a,z in zip(g,g[1:]):
            da,dz=dt.date.fromisoformat(a["date"]),dt.date.fromisoformat(z["date"])
            if (dz-da).days>=MIN_HOLD: out.append((a,z,da,dz))
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
    k=np.array([f"{'c' if 1-int(a['financed_base']) else 'f'}{'c' if 1-int(z['financed_base']) else 'f'}"
                for a,z,da,dz in P])
    A,B=res[k=="cf"],res[k=="fc"]
    if len(A)<50 or len(B)<50: return None
    return (A.mean()-B.mean())/2, len(A)+len(B), A.mean()+B.mean()

def boot(P,R=300):
    bb=np.array([a["bbl"] for a,z,da,dz in P]); u=np.unique(bb)
    idx={x:np.where(bb==x)[0] for x in u}; out=[]
    for _ in range(R):
        s=rng.choice(u,size=len(u),replace=True)
        Pb=[P[i] for i in np.concatenate([idx[x] for x in s])]
        try:
            v=pisym(Pb,excess(Pb))
            if v: out.append(v[0])
        except Exception: pass
    return np.percentile(out,[2.5,97.5]) if len(out)>30 else (np.nan,np.nan)

def row(label,P):
    if len(P)<300: print(f"{label:<28} {len(P):7,}   too few pairs"); return None
    v=pisym(P,excess(P))
    if not v: print(f"{label:<28} {len(P):7,}   too few switchers"); return None
    ci=boot(P); lo,hi=ci[0]-PS_HI, ci[1]-PS_LO
    vd="CLEARS" if lo>=BREAKEVEN else ("fails" if hi<BREAKEVEN else "ambiguous")
    print(f"{label:<28} {len(P):7,} {v[1]:7,} {v[0]:8.4f} [{ci[0]:8.4f},{ci[1]:7.4f}] "
          f"{v[2]:+8.4f} {vd:>10}")
    return dict(pairs=len(P),switch=v[1],pi=float(v[0]),ci=[float(ci[0]),float(ci[1])],
                asym=float(v[2]),verdict=vd)

out={}
print("="*94)
print("BOROUGH x PROPERTY TYPE   holding >= 36 months")
print("="*94)
print(f"{'market':<28} {'pairs':>7} {'switch':>7} {'pi':>8} {'95% CI':>20} {'asym':>8} {'verdict':>10}")
for b,name in BORO.items():
    for src in ["house","condo"]:
        r=row(f"{name} / {src}", build(rows,boro=b,src=src))
        if r: out[f"{name}/{src}"]=r
print()
print("="*94)
print("DISTRESS CHECK   drop the cheapest sales within borough x year")
print("="*94)
print(f"{'specification':<28} {'pairs':>7} {'switch':>7} {'pi':>8} {'95% CI':>20} {'asym':>8} {'verdict':>10}")
for lab,dl in [("all sales",None),("drop bottom 5%",0.05),("drop bottom 10%",0.10),("drop bottom 20%",0.20)]:
    for src in ["house","condo"]:
        r=row(f"{lab} / {src}", build(rows,src=src,drop_low=dl))
        if r: out[f"distress:{lab}/{src}"]=r
json.dump(out,open("breakdown_results.json","w"),indent=1)
print("\nwrote breakdown_results.json")
