"""Section 4 estimates on the four ACRIS boroughs.

ACRIS covers Manhattan, the Bronx, Brooklyn and Queens; Staten Island instruments are
recorded by the Richmond County Clerk. A deed-based financing flag therefore returns a
uniform and spurious 0.0% financed share on all 41,445 Staten Island sales. Those pairs
are all cash->cash and never enter the switching estimator, so excluding them changes no
coefficient -- only the pair counts. This script is the version whose numbers are in the
paper.

Reads panel2.csv.gz and dob_permits.csv.gz from the working directory. Seed 20260903.
"""
import gzip, csv, json, collections, datetime as dt, numpy as np, bisect

rng = np.random.default_rng(20260903)


def load(p="panel2.csv.gz"):
    with gzip.open(p,"rt",newline="") as fh: return list(csv.DictReader(fh))
def q(d): return (d.year-2016)*4 + (d.month-1)//3
def build(rows, mh=1096):
    by=collections.defaultdict(list)
    for r in rows: by[r["bbl"]].append(r)
    out=[]
    for b,rs in by.items():
        rs=sorted(rs,key=lambda r:r["date"])
        for a,z in zip(rs,rs[1:]):
            da,dz=dt.date.fromisoformat(a["date"]),dt.date.fromisoformat(z["date"])
            if (dz-da).days>=mh: out.append((a,z,da,dz))
    return out
def excess(P):
    bs=sorted({a["borough"] for a,z,_,_ in P}); nq=max(q(dz) for _,_,_,dz in P)+1
    cols={};j=0
    for b in bs:
        for t in range(1,nq): cols[(b,t)]=j; j+=1
    X=np.zeros((len(P),j)); y=np.array([np.log(float(z["price"]))-np.log(float(a["price"])) for a,z,_,_ in P])
    for i,(a,z,da,dz) in enumerate(P):
        b=a["borough"]
        if (b,q(da)) in cols: X[i,cols[(b,q(da))]]-=1
        if (b,q(dz)) in cols: X[i,cols[(b,q(dz))]]+=1
    beta,*_=np.linalg.lstsq(X,y,rcond=None); return y-X@beta
def kinds(P):
    return np.array([f"{'cash' if 1-int(a['financed_base']) else 'fin'}->{'cash' if 1-int(z['financed_base']) else 'fin'}" for a,z,_,_ in P])
def pisym(P,r,minn=60):
    k=kinds(P); A,B=r[k=="cash->fin"],r[k=="fin->cash"]
    if len(A)<minn or len(B)<minn: return None,len(A),len(B)
    return (A.mean()-B.mean())/2, len(A), len(B)
def boot(P,n=600):
    par=collections.defaultdict(list)
    for i,(a,z,_,_) in enumerate(P): par[a["bbl"]].append(i)
    keys=list(par); out=[]
    for _ in range(n):
        idx=[]
        for kk in rng.choice(len(keys),len(keys),replace=True): idx+=par[keys[kk]]
        Pb=[P[i] for i in idx]
        try:
            v=pisym(Pb,excess(Pb))[0]
            if v is not None: out.append(v)
        except Exception: pass
    return np.percentile(out,[2.5,97.5]) if len(out)>30 else (np.nan,np.nan)


allrows = load()
rows = [r for r in allrows if r["borough"] != "5"]
print(f"panel excluding Staten Island: {len(rows):,} of {len(allrows):,}")
MH = int(36*30.44)
out = {}

def summ(P, tag, bs=True):
    if len(P) < 300: print(f"  {tag:<34} {len(P):6,}  too few pairs"); return None
    r = excess(P); v = pisym(P, r)
    if v[0] is None: print(f"  {tag:<34} {len(P):6,}  too few switchers (cf {v[1]}, fc {v[2]})"); return None
    pi, cf, fc = v
    k = kinds(P); A, B = r[k=="cash->fin"], r[k=="fin->cash"]
    asym = A.mean()+B.mean()
    ci = boot(P) if bs else (np.nan, np.nan)
    print(f"  {tag:<34} {len(P):6,} cf {cf:5,} fc {fc:5,}  pi {pi:+.4f} "
          f"[{ci[0]:+.4f},{ci[1]:+.4f}]  A {asym:+.4f}", flush=True)
    return dict(pairs=len(P), cf=cf, fc=fc, pi=float(pi), ci=[float(ci[0]),float(ci[1])], asym=float(asym))

print("\nBY TYPE (36m)")
for src in ("house","condo"):
    out[src] = summ(build([r for r in rows if r["src"]==src], MH), src)

print("\nBY BOROUGH x TYPE (36m)")
BN = {"1":"Manhattan","2":"Bronx","3":"Brooklyn","4":"Queens"}
for b,name in BN.items():
    for src in ("house","condo"):
        v = summ(build([r for r in rows if r["src"]==src and r["borough"]==b], MH), f"{name}/{src}")
        if v: out[f"{name}/{src}"]=v

print("\nHOLDING SWEEP, houses")
sw=[]
for m in (12,24,36,48,60):
    P=build([r for r in rows if r["src"]=="house"], int(m*30.44))
    rr=excess(P); v=pisym(P,rr); k=kinds(P)
    A,B=rr[k=="cash->fin"],rr[k=="fin->cash"]
    se=0.5*np.sqrt(A.var(ddof=1)/len(A)+B.var(ddof=1)/len(B))
    print(f"  >= {m}m  {len(P):6,}  pi {v[0]:+.4f}  se {se:.4f}  A {A.mean()+B.mean():+.4f}")
    sw.append(dict(months=m,pairs=len(P),pi=float(v[0]),se=float(se),asym=float(A.mean()+B.mean())))
out["sweep_house"]=sw

print("\nTRANSITIONS, houses, 12m")
P=build([r for r in rows if r["src"]=="house"], int(12*30.44)); rr=excess(P); k=kinds(P)
tr={}
for kk in ("cash->fin","fin->cash","cash->cash","fin->fin"):
    v=rr[k==kk]; tr[kk]=dict(excess=float(v.mean()), se=float(v.std(ddof=1)/np.sqrt(len(v))), n=int(len(v)))
    print(f"  {kk:<12} {len(v):6,} {v.mean():+.4f} {v.std(ddof=1)/np.sqrt(len(v)):.4f}")
out["transitions_house_12m"]=tr

print("\nPOOLED (houses + condos), 36m")
out["pooled"]=summ(build([r for r in rows if r["src"] in ("house","condo")], MH), "pooled house+condo", bs=False)

print("\nPERMITS")
BORO={"MANHATTAN":1,"BRONX":2,"BROOKLYN":3,"QUEENS":4,"STATEN ISLAND":5}
perm=collections.defaultdict(list)
with gzip.open("dob_permits.csv.gz","rt") as fh:
    for r in csv.DictReader(fh):
        b=BORO.get((r["borough"] or "").strip().upper())
        try: blk,lot=int(r["block"]),int(r["lot"]); d=dt.datetime.strptime(r["issuance_date"].strip(),"%m/%d/%Y").date()
        except Exception: continue
        if not b or d.year<2010: continue
        perm[f"{b}{blk:05d}{lot:04d}"].append(d)
for kk in perm: perm[kk].sort()
def hasp(bbl,da,dz):
    v=perm.get(bbl)
    if not v: return False
    i=bisect.bisect_left(v,da); return i<len(v) and v[i]<=dz
for m in (36,24):
    PH=build([r for r in rows if r["src"]=="house"], int(m*30.44))
    fl=np.array([hasp(a["bbl"],da,dz) for a,z,da,dz in PH]); k=kinds(PH)
    print(f"  {m}m incidence:", {kk: round(float(fl[k==kk].mean()),3) for kk in ("cash->fin","fin->cash","cash->cash","fin->fin")},
          {kk: int((k==kk).sum()) for kk in ("cash->fin","fin->cash","cash->cash","fin->fin")})
    out[f"perm_incidence_{m}m"]={kk:[float(fl[k==kk].mean()), int((k==kk).sum())] for kk in ("cash->fin","fin->cash","cash->cash","fin->fin")}
    out[f"permfree_{m}m"]=summ([p for p,f in zip(PH,fl) if not f], f"{m}m permit-free", bs=(m==36))
    out[f"permitted_{m}m"]=summ([p for p,f in zip(PH,fl) if f], f"{m}m permitted", bs=False)
    out[f"all_{m}m"]=summ(PH, f"{m}m all", bs=(m==36))

print("\nDISTRESS (drop cheapest within borough x year), houses 36m")
def dropped(rs, frac):
    key=collections.defaultdict(list)
    for r in rs: key[(r["borough"],r["date"][:4])].append(float(r["price"]))
    cut={k:np.percentile(v,frac*100) for k,v in key.items()}
    return [r for r in rs if float(r["price"])>=cut[(r["borough"],r["date"][:4])]]
dd=[]
for f in (0,0.05,0.10,0.20):
    for src in ("house","condo"):
        base=[r for r in rows if r["src"]==src]
        P=build(dropped(base,f) if f else base, MH)
        v=pisym(P,excess(P))
        print(f"  drop {int(f*100)}% {src:<6} {len(P):6,}  pi {v[0]:+.4f}")
        dd.append(dict(frac=f,src=src,pairs=len(P),pi=float(v[0])))
out["distress"]=dd
json.dump(out, open("nosi_results.json","w"), indent=1)
print("\nwrote nosi_results.json")
