"""
Referee checks on Section 10 (bunching) of "The Execution-Certainty Wedge".
Runs offline against empirical/nyc_sales.json. Deterministic (seeds fixed).

Sections:
  T8   reproduce Table 8 with the author's estimator
  A    specification grid (degree, bin width, window, exclusion band)
  C    asymmetric exclusion band (below fixed at 50k, above widened)
  E    exact-threshold and charm-price counts at notches and placebo round numbers
  S    suppression of the exact-round-number spike at the three notches
  RN   polynomial + round-number-dummy counterfactual (Kleven-Waseem style), with bootstrap CIs
  D    minimum detectable effect at the $2M and $3M notches
  F    subgroup (property type, borough) and half-year estimates at $1M and $2M
  H    the $500k RPTT notch against clean placebos at $600k/$700k

Usage: python3 referee_bunching.py /path/to/nyc_sales.json
"""
import sys, json, itertools
import numpy as np

path = sys.argv[1] if len(sys.argv) > 1 else '/root/review/empirical/nyc_sales.json'
rows = json.load(open(path))
P = np.array([float(r["sale_price"]) for r in rows])
CLS = np.array([r["building_class_category"][:2] for r in rows])
BORO = np.array([r["borough"] for r in rows])
MONTH = np.array([r["sale_date"][:7] for r in rows])
TYPE = np.where(np.isin(CLS, ["01","02","03"]), "house", np.where(np.isin(CLS, ["09","10","17"]), "coop", "condo"))

# ---------------------------------------------------------------- estimators
def fit(p, thr, hw=300_000, bw=10_000, ex=50_000, ex_above=None, deg=5, exact="above"):
    """The author's estimator (bunching.py), with optional asymmetric band and exact-threshold handling.
    exact='above': a sale at exactly thr falls in the first above bin (author's convention; correct for
    thresholds that apply at 'thr or more'). exact='below': for thresholds that apply strictly above thr."""
    ex_above = ex if ex_above is None else ex_above
    lo, hi = thr - hw, thr + hw
    p = p[(p >= lo) & (p < hi)]
    if exact == "below": p = np.where(p == thr, thr - 1e-6, p)
    edges = np.arange(lo, hi + bw, bw); cnt, _ = np.histogram(p, bins=edges); mid = edges[:-1] + bw/2
    excl = (mid > thr - ex) & (mid < thr + ex_above)
    x = (mid - thr) / hw
    cf = np.polyval(np.polyfit(x[~excl], cnt[~excl], deg), x)
    below = (mid > thr - ex) & (mid <= thr); above = (mid > thr) & (mid < thr + ex_above)
    return dict(B=(cnt[below]-cf[below]).sum(), M=(cf[above]-cnt[above]).sum(), n=len(p),
                cf_above=cf[above].sum(), cnt=cnt, cf=cf, mid=mid)

def fit_rn(p, thr, hw=300_000, bw=10_000, ex=50_000, ex_above=None, deg=5, exact="above"):
    """Same, plus bin dummies for bins containing a multiple of $100k, $50k (not 100k), $25k (not 50k),
    estimated outside the excluded band and predicted inside it."""
    ex_above = ex if ex_above is None else ex_above
    lo, hi = thr - hw, thr + hw
    p = p[(p >= lo) & (p < hi)]
    if exact == "below": p = np.where(p == thr, thr - 1e-6, p)
    edges = np.arange(lo, hi + bw, bw); cnt, _ = np.histogram(p, bins=edges); mid = edges[:-1] + bw/2
    lo_e, hi_e = edges[:-1], edges[1:]
    if exact == "below": has = lambda k: (np.floor(hi_e/k)*k > lo_e)        # multiples fall in (lo, hi]
    else:                has = lambda k: (np.ceil(lo_e/k)*k < hi_e)         # multiples fall in [lo, hi)
    d100 = has(100_000).astype(float); d50 = (has(50_000) & ~has(100_000)).astype(float); d25 = (has(25_000) & ~has(50_000)).astype(float)
    excl = (mid > thr - ex) & (mid < thr + ex_above); x = (mid - thr)/hw
    X = np.column_stack([x**k for k in range(deg+1)] + [d100, d50, d25])
    beta, *_ = np.linalg.lstsq(X[~excl], cnt[~excl], rcond=None); cf = X @ beta
    below = (mid > thr - ex) & (mid <= thr); above = (mid > thr) & (mid < thr + ex_above)
    return dict(B=(cnt[below]-cf[below]).sum(), M=(cf[above]-cnt[above]).sum(), n=len(p), cf_above=cf[above].sum())

def boot(f, p, thr, R=1000, seed=20260901, **kw):
    rng = np.random.default_rng(seed); o = []
    for _ in range(R):
        s = rng.choice(p, size=len(p), replace=True)
        try: r = f(s, thr, **kw); o.append((r["B"], r["M"]))
        except Exception: pass
    return np.array(o)

def ci(a): return np.percentile(a, [2.5, 97.5])
def line(thr, r, bs):
    cB, cM = ci(bs[:,0]), ci(bs[:,1])
    return f"{thr:>10,} n={r['n']:6d}  B={r['B']:6.0f} [{cB[0]:5.0f},{cB[1]:5.0f}]  M={r['M']:6.0f} [{cM[0]:5.0f},{cM[1]:5.0f}]  M/cf_above={r['M']/r['cf_above']:5.2f}  sd(M)={bs[:,1].std():5.1f}"

# ---------------------------------------------------------------- T8
print("T8. Author's estimator, author's settings (deg 5, 10k bins, ±300k window, ±50k band), 1,000 bootstrap resamples")
for thr in (1_000_000, 2_000_000, 3_000_000, 900_000, 1_200_000, 1_500_000, 2_500_000):
    r = fit(P, thr); bs = boot(fit, P, thr); print("  " + line(thr, r, bs))

# ---------------------------------------------------------------- A
print("\nA. Specification grid: degree {2..7} x bin {5k,10k,20k,25k} x window {150k..500k} x band {30k..150k}")
grid = []
for deg, bw, hw, ex in itertools.product([2,3,4,5,6,7], [5_000,10_000,20_000,25_000], [150_000,200_000,300_000,400_000,500_000], [30_000,50_000,75_000,100_000,150_000]):
    if ex >= hw - 50_000 or (bw == 25_000 and ex % 25_000) or (bw == 20_000 and ex % 20_000): continue
    try: r1 = fit(P, 1_000_000, hw=hw, bw=bw, ex=ex, deg=deg); r2 = fit(P, 2_000_000, hw=hw, bw=bw, ex=ex, deg=deg)
    except Exception: continue
    grid.append((deg, bw, hw, ex, r1['B'], r1['M'], r2['B'], r2['M']))
g = np.array(grid)
print(f"  {len(g)} specifications. $1M: M>0 in {100*(g[:,5]>0).mean():.1f}%, M>300 in {100*(g[:,5]>300).mean():.1f}%; M median {np.median(g[:,5]):.0f}, 5th-95th pct [{np.percentile(g[:,5],5):.0f},{np.percentile(g[:,5],95):.0f}]; B median {np.median(g[:,4]):.0f}")
print(f"  $2M: M>0 in {100*(g[:,7]>0).mean():.1f}%; M median {np.median(g[:,7]):.0f}, 5th-95th pct [{np.percentile(g[:,7],5):.0f},{np.percentile(g[:,7],95):.0f}]")
bad = g[(g[:,5] < 300)]
print("  $1M specifications with M<300 (all are degree>=6 with window<=200k, or band>=75k with window<=150k):")
for b in bad: print(f"     deg={int(b[0])} bw={int(b[1])} hw={int(b[2])} ex={int(b[3])}: B={b[4]:.0f} M={b[5]:.0f}")

# ---------------------------------------------------------------- C
print("\nC. Below band fixed at 50k; above band widened (deg 5, 10k bins)")
for hw in (300_000, 400_000, 500_000):
    for exa in (50_000, 75_000, 100_000, 150_000):
        r1 = fit(P, 1_000_000, hw=hw, ex_above=exa); r2 = fit(P, 2_000_000, hw=hw, ex_above=exa); r3 = fit(P, 3_000_000, hw=hw, ex_above=exa)
        print(f"  window ±{hw//1000}k, above band {exa//1000}k: $1M B={r1['B']:5.0f} M={r1['M']:5.0f} (M/B={r1['M']/r1['B']:.2f}) | $2M B={r2['B']:4.0f} M={r2['M']:4.0f} | $3M B={r3['B']:4.0f} M={r3['M']:4.0f}")
r = fit(P, 1_000_000, hw=500_000, ex_above=250_000)
sel = (r['mid'] > 1_000_000) & (r['mid'] < 1_110_000)
print("  Hole extent at $1M (cf fitted with above band 250k, window ±500k): obs/cf by 10k bin from $1.00M:", " ".join(f"{c/f:.2f}" for c, f in zip(r['cnt'][sel], r['cf'][sel])))

# ---------------------------------------------------------------- E
print("\nE. Exact-threshold and charm-price counts. 'just-under share' = sales in (X-10k, X) / sales in (X-10k, X+10k)")
notch = {500_000:'RPTT 0.425% (>X)', 1_000_000:'1402-a 1.00%', 2_000_000:'1402-b 0.25%', 3_000_000:'1402-b+1402(a) 0.50%', 5_000_000:'1402-b 0.75%'}
print(f"  {'X':>10} {'notch':>22} | {'=X':>4} {'=X-1':>5} {'=X-1k':>5} {'=X-5k':>5} | {'(X-10k,X)':>9} {'[X,X+10k)':>9} | share")
for X in [400_000,500_000,600_000,700_000,800_000,900_000,1_000_000,1_100_000,1_200_000,1_300_000,1_500_000,1_750_000,2_000_000,2_250_000,2_500_000,3_000_000,3_500_000,4_000_000,5_000_000]:
    c = lambda v: int((P == v).sum()); ju = int(((P > X-10_000) & (P < X)).sum()); at = int(((P >= X) & (P < X+10_000)).sum())
    print(f"  {X:>10,} {notch.get(X,'-'):>22} | {c(X):4d} {c(X-1):5d} {c(X-1000):5d} {c(X-5000):5d} | {ju:9d} {at:9d} | {ju/(ju+at):.2f}")

# ---------------------------------------------------------------- S
print("\nS. Exact round-number spike relative to local non-round density (sales in (X-50k,X+50k) not at a 50k multiple, per 10k)")
for X in range(700_000, 3_400_001, 100_000):
    ex = int((P == X).sum()); win = P[(P > X-50_000) & (P < X+50_000)]; dens = len(win[(win % 50_000) != 0]) / 10.0
    print(f"  {X:>10,}: exact={ex:4d}  non-round/10k={dens:6.1f}  ratio={ex/dens:5.2f}" + ("   <-- notch" if X in notch else ""))

# ---------------------------------------------------------------- RN
print("\nRN. Polynomial + round-number dummies, 1,000 bootstrap resamples")
for label, kw in [("deg 5, ±300k, ±50k", {}), ("deg 5, ±400k, band 50k below / 100k above", dict(hw=400_000, ex_above=100_000))]:
    print("  --", label)
    for thr in (1_000_000, 2_000_000, 3_000_000, 1_500_000, 2_500_000, 1_750_000, 2_250_000):
        r = fit_rn(P, thr, **kw); bs = boot(fit_rn, P, thr, **kw); print("   " + line(thr, r, bs) + ("   (placebo)" if thr not in notch else ""))

# ---------------------------------------------------------------- D
print("\nD. Minimum detectable effect (80% power, 5% two-sided = 2.80 x bootstrap sd of M), author's specification")
r1 = fit(P, 1_000_000); share1 = r1['M'] / r1['cf_above']
for thr, notch_pct in [(2_000_000, 0.25), (3_000_000, 0.50)]:
    r = fit(P, thr); bs = boot(fit, P, thr); sd = bs[:,1].std(); mde = 2.80 * sd; up = ci(bs[:,1])[1]
    print(f"  ${thr:,}: cf_above={r['cf_above']:.0f}; sd(M)={sd:.1f}; MDE={mde:.0f} sales ({mde/r['cf_above']:.0%} of cf);"
          f" response proportional to $1M ({share1:.0%}) = {share1*r['cf_above']:.0f} sales -> {'detectable' if share1*r['cf_above']>mde else 'not detectable'};"
          f" response scaled by notch size ({notch_pct}/1.00) = {notch_pct*share1*r['cf_above']:.0f} sales -> {'detectable' if notch_pct*share1*r['cf_above']>mde else 'NOT detectable'};"
          f" 95% upper bound on M/cf = {up/r['cf_above']:.2f} = {up/r['cf_above']/share1:.0%} of the $1M response")

# ---------------------------------------------------------------- F
print("\nF. Subgroups and half-years at $1M and $2M (author's specification; 500 resamples)")
h1 = np.isin(MONTH, ['2025-08','2025-09','2025-10','2025-11','2025-12','2026-01'])
groups = [('house', TYPE=='house'), ('coop', TYPE=='coop'), ('condo', TYPE=='condo'), ('Manhattan', BORO=='1'), ('Brooklyn', BORO=='3'), ('Queens', BORO=='4'), ('Bronx+SI', np.isin(BORO,['2','5'])), ('Aug25-Jan26', h1), ('Feb26-Jul26', ~h1)]
for label, m in groups:
    p = P[m]
    for thr in (1_000_000, 2_000_000):
        r = fit(p, thr); bs = boot(fit, p, thr, R=500, seed=3); print(f"  {label:>12} " + line(thr, r, bs))
print("  Type composition by 50k bin across $1M (house/coop/condo shares):")
for lo in range(850_000, 1_200_000, 50_000):
    m = (P >= lo) & (P < lo + 50_000); n = m.sum()
    print(f"    [{lo:>9,},{lo+50_000:>9,}) n={n:5d}  " + "  ".join(f"{k}={100*(TYPE[m]==k).mean():4.1f}%" for k in ('house','coop','condo')))

# ---------------------------------------------------------------- H
print("\nH. $500k RPTT notch (higher rate applies strictly above $500,000, so exact-$500k sales are on the untaxed side) vs placebos; window ±200k (sample floor is $300k); round-number dummies; 500 resamples")
for thr in (500_000, 600_000, 700_000):
    for deg, ex, exa in [(3, 50_000, 50_000), (5, 50_000, 50_000), (3, 30_000, 60_000)]:
        kw = dict(hw=200_000, deg=deg, ex=ex, ex_above=exa, exact="below")
        r = fit_rn(P, thr, **kw); bs = boot(fit_rn, P, thr, R=500, seed=7, **kw)
        print(f"  deg={deg} band={ex//1000}/{exa//1000}k " + line(thr, r, bs) + ("   (placebo)" if thr != 500_000 else ""))
