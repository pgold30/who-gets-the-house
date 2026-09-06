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

rows=load()
res={}
# --- Staten Island houses ---
P=[p for p in build([r for r in rows if r["borough"]=="5" and r["src"]=="house"])]
k=kinds(P); c=collections.Counter(k)
print("Staten Island houses:",len(P),"pairs;",dict(c))
res["staten_island_house"]={"pairs":len(P),**{kk:int(vv) for kk,vv in c.items()}}

# --- permit-free bootstrap ---
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
PH=build([r for r in rows if r["src"]=="house"])
free=[p for p in PH if not hasp(p[0]["bbl"],p[2],p[3])]
pi,ncf,nfc=pisym(free,excess(free))
ci=boot(free)
print(f"permit-free houses: {len(free)} pairs, pi={pi:.4f}, bootstrap CI [{ci[0]:.4f},{ci[1]:.4f}], cf={ncf} fc={nfc}")
res["permit_free_boot"]={"pairs":len(free),"pi":float(pi),"ci":[float(ci[0]),float(ci[1])],"cf":ncf,"fc":nfc}
json.dump(res,open("verify2_results.json","w"),indent=1)
