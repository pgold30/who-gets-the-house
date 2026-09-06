"""Mortgage recording tax borne by the borrower, as a share of purchase price.

Section 5.2. The ACRIS match records the loan amount alongside the price, so the
statutory burden can be computed on each observed loan at its own size rather
than assumed at a representative loan-to-value ratio.
"""
import gzip, csv, json, numpy as np

rows = []
with gzip.open("panel2.csv.gz", "rt", newline="") as fh:
    for r in csv.DictReader(fh):
        rows.append(r)

pairs = []
for r in rows:
    if r["src"] != "house" or not int(r["financed_base"]):
        continue
    try:
        m, p = float(r.get("mort_amt") or 0), float(r["price"])
    except ValueError:
        continue
    if m > 0 and p > 0 and 0.05 < m / p <= 1.05:
        pairs.append((m, p))

ltv = np.array([m / p for m, p in pairs])
# 1.80% below $500,000, 1.925% at or above, borne by the borrower
share = np.array([(0.0180 if m < 500_000 else 0.01925) * m / p for m, p in pairs])

out = dict(n=len(pairs), mean_ltv=float(ltv.mean()), median_ltv=float(np.median(ltv)),
           mrt_share_of_price_mean=float(share.mean()),
           mrt_share_of_price_median=float(np.median(share)),
           mrt_p10=float(np.percentile(share, 10)),
           mrt_p90=float(np.percentile(share, 90)))
print(f"financed house purchases with an observed loan amount: {out['n']:,}")
print(f"  LTV        mean {out['mean_ltv']:.3f}  median {out['median_ltv']:.3f}")
print(f"  MRT/price  mean {out['mrt_share_of_price_mean']*100:.2f}%  "
      f"median {out['mrt_share_of_price_median']*100:.2f}%  "
      f"p10 {out['mrt_p10']*100:.2f}%  p90 {out['mrt_p90']*100:.2f}%")
json.dump(out, open("ltv_results.json", "w"), indent=1)
