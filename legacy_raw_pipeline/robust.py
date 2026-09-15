"""Robustness for the pre/post design: COVID, alternative period cuts,
bracket creep, bandwidth and polynomial degree."""
import json, numpy as np
from prepost import estimate, price, date, THRESH
rng = np.random.default_rng(20260903)

def sh(mask, thr, **kw):
    return estimate(price[mask], thr, **kw)["share"]

def dboot(m_pre, m_post, thr, R=400, **kw):
    a_, b_ = price[m_pre], price[m_post]
    out=[]
    for _ in range(R):
        try:
            ra=estimate(rng.choice(a_,len(a_),replace=True),thr,**kw)
            rb=estimate(rng.choice(b_,len(b_),replace=True),thr,**kw)
            out.append(rb["share"]-ra["share"])
        except Exception: pass
    return np.percentile(out,[2.5,97.5])

PRE  = date < "2019-04-01"
POST = date >= "2020-01-01"
CUTS = {
 "baseline: pre <2019-04, post >=2020-01": (PRE, POST),
 "drop COVID: post = 2022-2025":           (PRE, date >= "2022-01-01"),
 "clean pre: 2016-2018 only":              (date < "2019-01-01", POST),
 "tight: pre 2017-2018, post 2020-2021":   ((date>="2017-01-01")&(date<"2019-01-01"),
                                            (date>="2020-01-01")&(date<"2022-01-01")),
 "late only: post 2023-2025":              (PRE, date >= "2023-01-01"),
}
print("="*100)
print("PERIOD ROBUSTNESS   difference in missing-mass share (post - pre)")
print("="*100)
print(f"{'specification':<42} {'$1M (control)':>16} {'$2M':>22} {'$3M':>22}")
rows={}
for name,(a,b) in CUTS.items():
    cells=[]
    for thr in THRESH:
        d = sh(b,thr)-sh(a,thr)
        ci = dboot(a,b,thr) if thr!=1_000_000 else dboot(a,b,thr,R=250)
        cells.append((d,ci))
    rows[name]=[(float(d),[float(c) for c in ci]) for d,ci in cells]
    f=lambda c: f"{c[0]:+.3f} [{c[1][0]:+.2f},{c[1][1]:+.2f}]"
    print(f"{name:<42} {f(cells[0]):>16} {f(cells[1]):>22} {f(cells[2]):>22}")

print("\n"+"="*100)
print("ESTIMATOR ROBUSTNESS at $2,000,000   (baseline cut)")
print("="*100)
print(f"{'variant':<44} {'pre':>8} {'post':>8} {'diff':>8}")
VAR = {
 "baseline (w=400k, bin=10k, deg=5, band -50/+100)": {},
 "window 300k":  dict(window=300_000),
 "window 500k":  dict(window=500_000),
 "bins 20k":     dict(bw=20_000),
 "degree 3":     dict(deg=3),
 "degree 7":     dict(deg=7),
 "band -100/+150": dict(below=100_000, above=150_000),
 "no round-number controls": dict(controls=False),
}
est={}
for name,kw in VAR.items():
    a,b = sh(PRE,2_000_000,**kw), sh(POST,2_000_000,**kw)
    est[name]=dict(pre=float(a),post=float(b),diff=float(b-a))
    print(f"{name:<44} {a:8.3f} {b:8.3f} {b-a:8.3f}")

print("\n"+"="*100)
print("BRACKET CREEP   share of sample above each threshold, by year")
print("="*100)
yr=np.array([int(d[:4]) for d in date])
print(f"{'year':>6} {'n':>8} {'>$1M':>8} {'>$2M':>8} {'>$3M':>8}   median price")
creep={}
for y in range(2016,2026):
    m=yr==y; p=price[m]
    creep[y]=dict(n=int(m.sum()),above1=float((p>1e6).mean()),above2=float((p>2e6).mean()),
                  above3=float((p>3e6).mean()),median=float(np.median(p)))
    print(f"{y:>6} {m.sum():8,} {(p>1e6).mean():8.3f} {(p>2e6).mean():8.3f} {(p>3e6).mean():8.3f}   {np.median(p):12,.0f}")

json.dump({"periods":rows,"estimator":est,"creep":creep}, open("robust_results.json","w"), indent=1)
print("\nwrote robust_results.json")
