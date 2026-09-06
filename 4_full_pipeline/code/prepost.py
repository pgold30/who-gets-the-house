"""Pre/post s.1402-b difference-in-bunching, NYC residential sales 2016-2025.

Design. The 2019 New York budget created, effective for conveyances on or after
1 July 2019, (i) the s.1402-b supplemental tax, whose first bracket is 0.25% at
$2,000,000 and which steps to 0.50% at $3,000,000, and (ii) a rise in the state
base rate from 0.40% to 0.65% for residential conveyances of $3,000,000 or more.
So the $2M and $3M notches switch on at that date. The $1M mansion tax
(s.1402-a) has been 1% since 1989 and does not.

That gives two treated thresholds and one always-treated control in the same
market, with the pre-period serving as a placebo at the *same* price point -
which is a far stronger test than a fitted polynomial counterfactual alone.

Contracts entered into on or before 1 April 2019 were grandfathered, so sales
closing through 2019 may be untaxed even after 1 July. April-December 2019 is
therefore dropped as a transition window rather than assigned to either period.

Estimator is unchanged from bunching_v2.py (deposited with version 2 of the
archive): fifth-degree polynomial counterfactual in a +/-$400k window, $10k bins,
asymmetric exclusion band (-$50k, +$100k) following Kopczuk and Munroe, dummies
for exact multiples of $100k/$50k/$25k, and the bin containing the threshold
assigned to the taxed side because the notches apply at "or more".
"""
import json, numpy as np
rng = np.random.default_rng(20260903)

rows = json.load(open("sample_2016_2025.json"))
price = np.array([float(r["sale_price"]) for r in rows])
date  = np.array([r["sale_date"][:10] for r in rows])

PRE   = date <  "2019-04-01"
TRANS = (date >= "2019-04-01") & (date < "2020-01-01")
POST  = date >= "2020-01-01"

THRESH = {1_000_000: ("$1M mansion tax", "1989 - unchanged"),
          2_000_000: ("$2M s.1402-b",    "from 1 Jul 2019"),
          3_000_000: ("$3M s.1402-b + base", "from 1 Jul 2019")}
PLACEBOS = [1_500_000, 1_750_000, 2_250_000, 2_500_000]


def round_dummies(mid, bw):
    return np.column_stack([((np.round(mid/bw)*bw) % m == 0).astype(float)
                            for m in (100_000, 50_000, 25_000)])


def estimate(p, thr, window=400_000, bw=10_000, below=50_000, above=100_000,
             deg=5, controls=True):
    lo, hi = thr-window, thr+window
    sel = p[(p >= lo) & (p < hi)]
    edges = np.arange(lo, hi+bw, bw)
    cnt, _ = np.histogram(sel, bins=edges)
    mid = edges[:-1] + bw/2
    excl = (mid > thr-below) & (mid < thr+above)
    X = np.column_stack([((mid-thr)/window)**k for k in range(deg+1)])
    if controls:
        X = np.column_stack([X, round_dummies(mid, bw)])
    beta, *_ = np.linalg.lstsq(X[~excl], cnt[~excl], rcond=None)
    cf = X @ beta
    b_reg = (mid > thr-below) & (mid < thr)
    a_reg = (mid > thr) & (mid < thr+above)
    B = (cnt[b_reg]-cf[b_reg]).sum()
    M = (cf[a_reg]-cnt[a_reg]).sum()
    ca = cf[a_reg].sum()
    return dict(B=B, M=M, cf_above=ca, share=M/ca if ca > 0 else np.nan,
                n=len(sel), mid=mid, cnt=cnt, cf=cf, thr=thr)


def boot(p, thr, R=600):
    out = []
    for _ in range(R):
        s = rng.choice(p, size=len(p), replace=True)
        try:
            r = estimate(s, thr); out.append((r["M"], r["share"]))
        except Exception:
            pass
    return np.array(out)


def run(mask, label, R=600):
    p = price[mask]
    print(f"\n{'='*94}\n{label}   n = {len(p):,}   ({np.sort(date[mask])[0]} to {np.sort(date[mask])[-1]})\n{'='*94}")
    print(f"{'threshold':>11} {'status':<22} {'n win':>7} {'B':>7} {'M':>7} "
          f"{'M 95% CI':>18} {'M/cf':>7} {'sig':>4}")
    res = {}
    for thr, (name, status) in THRESH.items():
        r = estimate(p, thr); bs = boot(p, thr, R)
        ci = np.percentile(bs[:, 0], [2.5, 97.5])
        sh = np.percentile(bs[:, 1], [2.5, 97.5])
        sig = "yes" if ci[0] > 0 else "no"
        res[thr] = dict(M=float(r["M"]), B=float(r["B"]), share=float(r["share"]),
                        M_ci=[float(c) for c in ci], share_ci=[float(c) for c in sh],
                        n=int(r["n"]), sd=float(bs[:, 0].std(ddof=1)),
                        cf_above=float(r["cf_above"]))
        print(f"{thr:11,} {status:<22} {r['n']:7,} {r['B']:7.0f} {r['M']:7.0f} "
              f"[{ci[0]:7.0f},{ci[1]:7.0f}] {r['share']:7.2f} {sig:>4}")
    print()
    for thr in PLACEBOS:
        r = estimate(p, thr); bs = boot(p, thr, R//2)
        ci = np.percentile(bs[:, 0], [2.5, 97.5])
        sig = "yes" if ci[0] > 0 else "no"
        res[thr] = dict(M=float(r["M"]), M_ci=[float(c) for c in ci], placebo=True)
        print(f"{thr:11,} {'(placebo, no notch)':<22} {r['n']:7,} {r['B']:7.0f} {r['M']:7.0f} "
              f"[{ci[0]:7.0f},{ci[1]:7.0f}] {'':>7} {sig:>4}")
    return res


print(f"sample: {len(price):,} sales, {np.sort(date)[0]} to {np.sort(date)[-1]}")
print(f"  pre  (< 2019-04-01)            : {PRE.sum():,}")
print(f"  transition (Apr-Dec 2019, dropped): {TRANS.sum():,}")
print(f"  post (>= 2020-01-01)           : {POST.sum():,}")

out = {"pre": run(PRE, "PRE-TREATMENT  Jan 2016 - Mar 2019   ($2M and $3M notches DO NOT EXIST)"),
       "post": run(POST, "POST-TREATMENT Jan 2020 - Dec 2025   ($2M and $3M notches IN FORCE)"),
       "pooled": run(np.ones(len(price), bool), "POOLED 2016-2025 (for comparison with the published estimate)")}
json.dump(out, open("prepost_results.json", "w"), indent=1)
print("\nwrote prepost_results.json")
