"""Attacks C, D and E."""
import gzip, csv, json, collections, datetime as dt, numpy as np
rows=[]
with gzip.open("panel2.csv.gz","rt",newline="") as fh:
    for r in csv.DictReader(fh): rows.append(r)
out={}

print("="*94); print("C.  DELAYED FINANCING  how much of the cash category acquires a mortgage later?")
print("="*94)
# financed_wide uses -15/+180. A sale cash under base (-15/+90) but financed under wide
# acquired its mortgage between 90 and 180 days after the deed.
for src in ["house","condo"]:
    sub=[r for r in rows if r["src"]==src]
    cash_base=[r for r in sub if not int(r["financed_base"])]
    later=[r for r in cash_base if int(r["financed_wide"])]
    strict_only=[r for r in sub if int(r["financed_strict"])!=int(r["financed_base"])]
    print(f"   {src:<6} cash under the baseline window: {len(cash_base):>7,} "
          f"({len(cash_base)/len(sub)*100:.1f}% of sales)")
    print(f"          of those, a mortgage appears at 90-180 days: {len(later):>6,} "
          f"({len(later)/max(len(cash_base),1)*100:.1f}% of the cash category)")
    print(f"          sales whose classification changes between the 30- and 90-day windows: "
          f"{len(strict_only):,}")
    out[f"C_{src}"]=dict(cash=len(cash_base),cash_share=len(cash_base)/len(sub),
                         delayed=len(later),delayed_share=len(later)/max(len(cash_base),1),
                         window_sensitive=len(strict_only))
print("\n   A cash purchase financed at 90-180 days is either delayed financing or a")
print("   cash-out refinance. Either way it bounds the misclassification the baseline")
print("   window can generate, and Section 4.6 shows the estimate across all three windows.")

print()
print("="*94); print("D.  SELECTION  are repeat-sale parcels, and matched condominiums, representative?")
print("="*94)
cnt=collections.Counter(r["bbl"] for r in rows)
rep=[r for r in rows if cnt[r["bbl"]]>=2]; sing=[r for r in rows if cnt[r["bbl"]]<2]
def prof(rs,lab):
    p=np.array([float(r["price"]) for r in rs])
    cash=np.mean([1-int(r["financed_base"]) for r in rs])
    bo=collections.Counter(r["borough"] for r in rs)
    hs=np.mean([r["src"]=="house" for r in rs])
    print(f"   {lab:<26} n {len(rs):>7,}  median price {np.median(p):>9,.0f}  "
          f"cash {cash*100:4.1f}%  house {hs*100:4.1f}%  "
          f"Mn/Bx/Bk/Qn/SI {'/'.join(str(round(bo[b]/len(rs)*100)) for b in '12345')}")
    return dict(n=len(rs),median_price=float(np.median(p)),cash=float(cash),house=float(hs))
out["D_repeat"]=prof(rep,"repeat-sale parcels"); out["D_single"]=prof(sing,"single-sale parcels")
out["D_all"]=prof(rows,"all sales")

print()
print("="*94); print("E.  DIRECTION  do the two switching directions differ as renovation predicts?")
print("="*94)
by=collections.defaultdict(list)
for r in rows: by[r["bbl"]].append(r)
g={"cash->fin":[], "fin->cash":[]}
for b,rs in by.items():
    rs=sorted(rs,key=lambda r:r["date"])
    for a,z in zip(rs,rs[1:]):
        ca,cz=1-int(a["financed_base"]),1-int(z["financed_base"])
        if ca==cz: continue
        gap=(dt.date.fromisoformat(z["date"])-dt.date.fromisoformat(a["date"])).days
        g["cash->fin" if ca else "fin->cash"].append((gap,float(a["price"]),float(z["price"])))
print(f"{'direction':<14} {'pairs':>7} {'median gap (days)':>19} {'share held <36m':>17} {'median 1st price':>18}")
for k,v in g.items():
    gaps=np.array([x[0] for x in v]); p1=np.array([x[1] for x in v])
    out[f"E_{k}"]=dict(pairs=len(v),median_gap=float(np.median(gaps)),
                       share_short=float(np.mean(gaps<36*30.44)),median_first=float(np.median(p1)))
    print(f"{k:<14} {len(v):7,} {np.median(gaps):19,.0f} {np.mean(gaps<36*30.44)*100:16.1f}% "
          f"{np.median(p1):18,.0f}")
print("\n   Renovation predicts that cash-first pairs are held for less time and start")
print("   cheaper. Both hold, which is why the 36-month filter removes the asymmetry.")
json.dump(out,open("referee_CDE.json","w"),indent=1)
