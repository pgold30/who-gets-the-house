"""Are the matched condominium sales representative of all condominium sales?

The deed-match recovers 71.4% of condominium sales. The 99.6% validation on
houses shows the recovered LOT is right; it says nothing about whether the
matched subsample is REPRESENTATIVE. This compares the two directly.
"""
import json, gzip, csv, collections, datetime as dt, numpy as np
from condo_match import load_legals, load_master, index_deeds, match, CONDO_CODES, SALES

legals=load_legals(); deeds,_=load_master()
sales=json.load(open(SALES))
ix=index_deeds(deeds,legals,1001,1999)
matched,_=match(sales,ix,CONDO_CODES)
mkeys={(str(s.get("bbl")),s["sale_date"][:10],s["sale_price"]) for s,_ in matched}

allc=[s for s in sales if (s.get("building_class_category") or "").strip()[:2] in CONDO_CODES
      and len(str(s.get("bbl") or ""))==10]
mm=[s for s in allc if (str(s.get("bbl")),s["sale_date"][:10],s["sale_price"]) in mkeys]
uu=[s for s in allc if (str(s.get("bbl")),s["sale_date"][:10],s["sale_price"]) not in mkeys]

def prof(rs,lab):
    p=np.array([float(s["sale_price"]) for s in rs])
    yr=collections.Counter(s["sale_date"][:4] for s in rs)
    bo=collections.Counter(str(s["bbl"])[0] for s in rs)
    print(f"   {lab:<22} n {len(rs):>7,}  median {np.median(p):>10,.0f}  "
          f"p25 {np.percentile(p,25):>9,.0f}  p75 {np.percentile(p,75):>10,.0f}  "
          f"Mn/Bx/Bk/Qn/SI {'/'.join(str(round(bo[b]/len(rs)*100)) for b in '12345')}")
    return dict(n=len(rs),median=float(np.median(p)),p25=float(np.percentile(p,25)),
                p75=float(np.percentile(p,75)),
                boro={b:bo[b]/len(rs) for b in '12345'},
                yr={y:yr[y]/len(rs) for y in sorted(yr)})
print("="*94); print("MATCHED vs UNMATCHED CONDOMINIUM SALES"); print("="*94)
out={"matched":prof(mm,"matched (71.4%)"),"unmatched":prof(uu,"unmatched (28.6%)"),
     "all":prof(allc,"all condominiums")}
print()
print(f"   {'year':>6} {'matched share':>15}")
for y in sorted(out['matched']['yr']):
    my=out['matched']['yr'][y]*len(mm); ay=my+out['unmatched']['yr'].get(y,0)*len(uu)
    print(f"   {y:>6} {my/max(ay,1)*100:14.1f}%")
json.dump(out,open("condo_selection.json","w"),indent=1)
print("\nwrote condo_selection.json")
