"""Do cash and financed buyers bunch differently at the transfer-tax notches?

This is the test that ties the notch experiment to the rest of the paper. The
first five sections are about the cash-versus-financed margin; Section 6, as
first written, was about transaction bunching for all buyers together.

The hypothesis is specific. Crossing a notch requires liquid cash at closing -
$10,000 at the $1,000,000 mansion-tax cliff - and a financed buyer has already
committed their liquidity to the down payment, the mortgage recording tax and
closing costs. A cash buyer has not. If liquidity at closing is what binds,
FINANCED buyers should bunch below a notch more than cash buyers do.

Uses the merged panel (houses + condominiums) with the ACRIS financing flag.
"""
import gzip, csv, json, collections, numpy as np, datetime as dt
rng = np.random.default_rng(20260903)

rows = []
with gzip.open("panel2.csv.gz", "rt", newline="") as fh:
    for r in csv.DictReader(fh):
        rows.append(r)
print(f"panel: {len(rows):,} sales")

THRESH = {1_000_000: "$1M mansion tax (1.00 pt)",
          2_000_000: "$2M s.1402-b (0.25 pt)",
          3_000_000: "$3M s.1402-b + base (0.50 pt)",
          500_000:   "$500k NYC RPTT step (0.425 pt)"}
PLACEBO = [1_500_000, 1_750_000, 2_250_000, 2_500_000]


def round_dummies(mid, bw):
    return np.column_stack([((np.round(mid/bw)*bw) % m == 0).astype(float)
                            for m in (100_000, 50_000, 25_000)])


def estimate(p, thr, window=400_000, bw=10_000, below=50_000, above=100_000, deg=5):
    lo, hi = thr-window, thr+window
    sel = p[(p >= lo) & (p < hi)]
    if len(sel) < 400:
        return None
    edges = np.arange(lo, hi+bw, bw)
    cnt, _ = np.histogram(sel, bins=edges)
    mid = edges[:-1] + bw/2
    excl = (mid > thr-below) & (mid < thr+above)
    X = np.column_stack([((mid-thr)/window)**k for k in range(deg+1)])
    X = np.column_stack([X, round_dummies(mid, bw)])
    beta, *_ = np.linalg.lstsq(X[~excl], cnt[~excl], rcond=None)
    cf = X @ beta
    a_reg = (mid > thr) & (mid < thr+above)
    ca = cf[a_reg].sum()
    if ca <= 0:
        return None
    return float((cf[a_reg]-cnt[a_reg]).sum()/ca), len(sel)


def boot(p, thr, R=400):
    out = []
    for _ in range(R):
        s = rng.choice(p, size=len(p), replace=True)
        v = estimate(s, thr)
        if v:
            out.append(v[0])
    return np.percentile(out, [2.5, 97.5]) if len(out) > 30 else (np.nan, np.nan)


# post-reform only for the 2019 thresholds; all years for $1M and $500k
def subset(cash, post_only):
    out = []
    for r in rows:
        if r["borough"] == "5":
            continue
        if (1-int(r["financed_base"])) != cash:
            continue
        if post_only and r["date"] < "2020-01-01":
            continue
        out.append(float(r["price"]))
    return np.array(out)


print()
print("="*98)
print("MISSING MASS ABOVE THE THRESHOLD, BY BUYER TYPE")
print("="*98)
print(f"{'threshold':<32} {'period':<12} {'cash':>22} {'financed':>22} {'gap':>8}")
res = {}
for thr, lab in THRESH.items():
    post = thr in (2_000_000, 3_000_000)
    per = "2020-2025" if post else "2016-2025"
    pc, pf = subset(1, post), subset(0, post)
    vc, vf = estimate(pc, thr), estimate(pf, thr)
    if not vc or not vf:
        print(f"{lab:<32} {per:<12}   too few")
        continue
    cic, cif = boot(pc, thr), boot(pf, thr)
    res[str(thr)] = dict(label=lab, period=per,
                         cash=vc[0], cash_ci=[float(cic[0]), float(cic[1])], cash_n=vc[1],
                         fin=vf[0], fin_ci=[float(cif[0]), float(cif[1])], fin_n=vf[1],
                         gap=vf[0]-vc[0])
    print(f"{lab:<32} {per:<12} {vc[0]:7.3f} [{cic[0]:6.3f},{cic[1]:6.3f}] "
          f"{vf[0]:7.3f} [{cif[0]:6.3f},{cif[1]:6.3f}] {vf[0]-vc[0]:+8.3f}")

print()
print(f"{'placebos (2016-2025)':<32}")
for thr in PLACEBO:
    pc, pf = subset(1, False), subset(0, False)
    vc, vf = estimate(pc, thr), estimate(pf, thr)
    if not vc or not vf:
        continue
    res[str(thr)] = dict(label=f"${thr/1e6:.2f}M placebo", cash=vc[0], fin=vf[0], gap=vf[0]-vc[0])
    print(f"{'  $'+format(thr,',')+' (no notch)':<32} {'':<12} {vc[0]:7.3f} {'':<15} "
          f"{vf[0]:7.3f} {'':<15} {vf[0]-vc[0]:+8.3f}")

print()
print("="*98)
print("CHARM PRICES BY BUYER TYPE   sales at exactly $X-1")
print("="*98)
print(f"{'price point':>12} {'cash at X-1':>12} {'fin at X-1':>11} {'cash at X':>11} {'fin at X':>10}")
charm = {}
allp = {1: subset(1, False), 0: subset(0, False)}
for x in [500_000, 1_000_000, 2_000_000, 3_000_000, 1_500_000, 2_500_000]:
    row = {}
    for c in (1, 0):
        p = allp[c]
        row["cash" if c else "fin"] = dict(m1=int((p == x-1).sum()), at=int((p == x).sum()))
    charm[str(x)] = row
    print(f"{x:12,} {row['cash']['m1']:12,} {row['fin']['m1']:11,} "
          f"{row['cash']['at']:11,} {row['fin']['at']:10,}")

json.dump({"bunching": res, "charm": charm}, open("notch_financing_results.json", "w"), indent=1)
print("\nwrote notch_financing_results.json")
