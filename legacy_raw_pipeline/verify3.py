import gzip, csv, json, collections, datetime as dt, numpy as np, bisect
exec(open("verify2.py").read().split("rows=load()")[0])
rows = load()
MH = int(36*30.44)
out = {}

# ---- condo & house MRT burden ----
def burden(src):
    pr=[]
    for r in rows:
        if r["src"]!=src or not int(r["financed_base"]): continue
        try: m,p=float(r.get("mort_amt") or 0), float(r["price"])
        except ValueError: continue
        if m>0 and p>0 and 0.05<m/p<=1.05: pr.append((m,p))
    ltv=np.array([m/p for m,p in pr]); sh=np.array([(0.0180 if m<500_000 else 0.01925)*m/p for m,p in pr])
    return dict(n=len(pr), ltv_mean=float(ltv.mean()), ltv_med=float(np.median(ltv)),
                mean=float(sh.mean()), med=float(np.median(sh)),
                p10=float(np.percentile(sh,10)), p90=float(np.percentile(sh,90)))
# condo loan amounts are not in panel2; recover them from ACRIS directly
MA={}
with gzip.open("acris_master.csv.gz","rt") as fh:
    for x in csv.DictReader(fh):
        if x["doc_type"]!="MTGE": continue
        try: MA[x["document_id"]]=(dt.date.fromisoformat(x["document_date"][:10]), float(x["document_amt"] or 0))
        except Exception: pass
mort=collections.defaultdict(list)
with gzip.open("acris_legals.csv.gz","rt") as fh:
    for x in csv.DictReader(fh):
        v=MA.get(x["document_id"])
        if not v: continue
        try: b=f'{int(x["borough"])}{int(x["block"]):05d}{int(x["lot"]):04d}'
        except Exception: continue
        mort[b].append(v)
for k in mort: mort[k].sort()
def loan(bbl,d,lo=-15,hi=90):
    best=0
    for dd,amt in mort.get(bbl,[]):
        if lo<=(dd-d).days<=hi: best=max(best,amt)
    return best
def burden2(src):
    pr=[]
    for r in rows:
        if r["src"]!=src or not int(r["financed_base"]) or r["borough"]=="5": continue
        p=float(r["price"]); m=float(r.get("mort_amt") or 0) or loan(r["bbl"], dt.date.fromisoformat(r["date"]))
        if m>0 and p>0 and 0.05<m/p<=1.05: pr.append((m,p))
    ltv=np.array([m/p for m,p in pr]); sh=np.array([(0.0180 if m<500_000 else 0.01925)*m/p for m,p in pr])
    return dict(n=len(pr), ltv_mean=float(ltv.mean()), ltv_med=float(np.median(ltv)),
                mean=float(sh.mean()), med=float(np.median(sh)),
                p10=float(np.percentile(sh,10)), p90=float(np.percentile(sh,90)))
for s in ("house","condo"):
    out[f"mrt_{s}"]=burden2(s)
    b=out[f"mrt_{s}"]
    print(f"{s}: n={b['n']:,} LTV mean {b['ltv_mean']:.3f} med {b['ltv_med']:.3f}  "
          f"MRT/price mean {b['mean']*100:.2f}% med {b['med']*100:.2f}% "
          f"p10 {b['p10']*100:.2f}% p90 {b['p90']*100:.2f}%", flush=True)

# ---- CEMA ----
cm={}
with gzip.open("cema_master.csv.gz","rt") as fh:
    for x in csv.DictReader(fh):
        try: cm[x["document_id"]]=(dt.date.fromisoformat(x["document_date"][:10]), float(x["document_amt"] or 0))
        except Exception: pass
cema=collections.defaultdict(list)
with gzip.open("cema_legals.csv.gz","rt") as fh:
    for x in csv.DictReader(fh):
        v=cm.get(x["document_id"])
        if not v: continue
        try: b=f'{int(x["borough"])}{int(x["block"]):05d}{int(x["lot"]):04d}'
        except Exception: continue
        cema[b].append(v)
for k in cema: cema[k].sort()
print(f"CEMA: {len(cm):,} M&CON documents, {sum(len(v) for v in cema.values()):,} parcel-links on {len(cema):,} parcels")

def near(bbl, d, lo=-15, hi=90):
    v=cema.get(bbl)
    if not v: return None
    for dd,amt in v:
        if lo<=(dd-d).days<=hi: return amt
    return None

n_cash=n_cash_cema=n_fin=n_fin_cema=0; camts=[]
for r in rows:
    if r["src"] not in ("house","condo") or r["borough"]=="5": continue
    d=dt.date.fromisoformat(r["date"]); a=near(r["bbl"], d)
    if int(r["financed_base"]):
        n_fin+=1; n_fin_cema += a is not None
    else:
        n_cash+=1
        if a is not None:
            n_cash_cema+=1; camts.append((a, float(r["price"])))
print(f"  purchases flagged CASH with a concurrent M&CON: {n_cash_cema:,} of {n_cash:,} = {n_cash_cema/n_cash*100:.2f}%")
print(f"  purchases flagged FINANCED with a concurrent M&CON: {n_fin_cema:,} of {n_fin:,} = {n_fin_cema/n_fin*100:.2f}%")
out["cema"]=dict(docs=len(cm), parcels=len(cema), cash=n_cash, cash_cema=n_cash_cema,
                 fin=n_fin, fin_cema=n_fin_cema)

# ---- reclassify cash-with-CEMA as financed, re-estimate houses ----
rw=[dict(r) for r in rows if r["borough"]!="5"]
flip=0
for r in rw:
    if not int(r["financed_base"]):
        d=dt.date.fromisoformat(r["date"])
        if near(r["bbl"], d) is not None:
            r["financed_base"]="1"; flip+=1
print(f"  reclassified {flip:,} sales from cash to financed")
for tag,src in (("houses","house"),("condos","condo")):
    P=build([r for r in rw if r["src"]==src], MH)
    pi,cf,fc=pisym(P,excess(P))
    print(f"  {tag} after CEMA reclassification: pi={pi:+.4f}  pairs {len(P):,}  cf {cf} fc {fc}")
    out[f"cema_reclass_{tag}"]=dict(pi=float(pi),pairs=len(P),cf=cf,fc=fc)

# ---- permit-free bootstrap at 1095 days ----
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
PH=build([r for r in rows if r["src"]=="house"], MH)
free=[p for p in PH if not hasp(p[0]["bbl"],p[2],p[3])]
pi,cf,fc=pisym(free,excess(free)); ci=boot(free)
print(f"permit-free houses (1095d): {len(free):,} pairs pi={pi:.4f} CI [{ci[0]:.4f},{ci[1]:.4f}] cf={cf} fc={fc}")
out["permit_free"]=dict(pairs=len(free),pi=float(pi),ci=[float(ci[0]),float(ci[1])],cf=cf,fc=fc)
json.dump(out,open("verify3_results.json","w"),indent=1)
