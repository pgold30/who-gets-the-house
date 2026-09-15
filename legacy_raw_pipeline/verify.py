"""Independent verification: a fully non-parametric difference-in-differences on
raw counts, with no counterfactual polynomial anywhere. If this agrees with the
bunching estimates, the result is not an artefact of the fitted counterfactual.

R(X) = count in [X, X+100k) / count in [X-150k, X-50k)
A notch at X should lower R. Nothing else about the price density should.
"""
import json, numpy as np
from prepost import price, date, THRESH, PLACEBOS
rng = np.random.default_rng(20260903)
PRE, POST = date < "2019-04-01", date >= "2020-01-01"
pre_p, post_p = price[PRE], price[POST]

def R(p, x):
    up = ((p >= x) & (p < x+100_000)).sum()
    dn = ((p >= x-150_000) & (p < x-50_000)).sum()
    return up/dn if dn else np.nan

def did(x, R_=2000):
    d = []
    for _ in range(R_):
        a = rng.choice(pre_p, len(pre_p), replace=True)
        b = rng.choice(post_p, len(post_p), replace=True)
        d.append(np.log(R(b, x)) - np.log(R(a, x)))
    return np.percentile(d, [2.5, 97.5])

print("="*96)
print("NON-PARAMETRIC DiD   R = count[X, X+100k) / count[X-150k, X-50k)   no polynomial used")
print("="*96)
print(f"{'threshold':>11} {'R pre':>8} {'R post':>8} {'log change':>11} {'95% CI':>20}   status")
out = {}
for x in list(THRESH) + PLACEBOS:
    ra, rb = R(pre_p, x), R(post_p, x)
    lc = np.log(rb) - np.log(ra); ci = did(x)
    st = ("notch from Jul 2019" if x in (2_000_000, 3_000_000)
          else "notch since 1989" if x == 1_000_000 else "no notch (placebo)")
    out[str(x)] = dict(R_pre=float(ra), R_post=float(rb), log_change=float(lc),
                       ci=[float(c) for c in ci], status=st)
    print(f"{x:11,} {ra:8.3f} {rb:8.3f} {lc:+11.3f} [{ci[0]:+8.3f},{ci[1]:+8.3f}]   {st}")

print("\nPrediction: negative and significant at $2M and $3M only; zero at $1M and placebos.")

# sanity: does the published 12-month window reproduce inside the big file?
print("\n" + "="*96)
print("SANITY   published estimate vs the same months inside the annualized file")
print("="*96)
from prepost import estimate
old = np.array([float(r["sale_price"]) for r in json.load(open("/home/claude/empirical/nyc_sales.json"))])
win = (date >= "2025-01-01")
for thr in THRESH:
    a = estimate(old, thr)["share"]
    b = estimate(price[win], thr)["share"]
    print(f"  {thr:11,}   published window (Aug25-Jul26) {a:6.3f}   annualized 2025 {b:6.3f}")

json.dump(out, open("verify_results.json", "w"), indent=1)
print("\nwrote verify_results.json")
