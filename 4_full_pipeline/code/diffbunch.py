"""Difference-in-bunching with a bootstrap CI on the difference itself, a
placebo-based yardstick for specification error, and estimator-free evidence."""
import json, numpy as np
from prepost import estimate, price, date, PRE, POST, THRESH, PLACEBOS
rng = np.random.default_rng(20260903)

pre_p, post_p = price[PRE], price[POST]

def diff_boot(thr, R=600):
    out = []
    for _ in range(R):
        a = rng.choice(pre_p,  size=len(pre_p),  replace=True)
        b = rng.choice(post_p, size=len(post_p), replace=True)
        try:
            ra, rb = estimate(a, thr), estimate(b, thr)
            out.append(rb["share"] - ra["share"])
        except Exception:
            pass
    return np.array(out)

print("="*92)
print("DIFFERENCE-IN-BUNCHING   share of counterfactual mass missing above threshold")
print("="*92)
print(f"{'threshold':>11} {'pre':>8} {'post':>8} {'post-pre':>9} {'95% CI on difference':>24}")
res = {}
for thr in list(THRESH) + PLACEBOS:
    ra, rb = estimate(pre_p, thr), estimate(post_p, thr)
    d = diff_boot(thr, 600 if thr in THRESH else 300)
    ci = np.percentile(d, [2.5, 97.5])
    res[thr] = dict(pre=float(ra["share"]), post=float(rb["share"]),
                    diff=float(rb["share"]-ra["share"]), diff_ci=[float(c) for c in ci])
    tag = "" if thr in THRESH else "  (placebo)"
    print(f"{thr:11,} {ra['share']:8.3f} {rb['share']:8.3f} "
          f"{rb['share']-ra['share']:9.3f} [{ci[0]:9.3f},{ci[1]:9.3f}]{tag}")

pl = [abs(res[t]["post"]) for t in PLACEBOS]
print(f"\nSpecification-error yardstick: |share| at the four placebos, post period")
print(f"  {['%.3f'%x for x in pl]}   max {max(pl):.3f}, mean {np.mean(pl):.3f}")
print("  A live-threshold estimate is credible only if it clears this scale.")

print("\n" + "="*92)
print("ESTIMATOR-FREE EVIDENCE  focal-price spike at exactly X, and charm price at X-1")
print("="*92)
def local_density(p, x, half=25_000):
    near = p[(p > x-half) & (p < x+half) & (p % 10_000 != 0)]
    return len(near) / (2*half) * 10_000     # expected count in a 10k-wide focal cell

print(f"{'price point':>12} | {'PRE  spike':>10} {'ratio':>7} {'X-1':>5} | {'POST spike':>11} {'ratio':>7} {'X-1':>5}")
spikes = {}
for x in [1_000_000, 2_000_000, 3_000_000, 1_500_000, 2_500_000]:
    sa, sb = int((pre_p == x).sum()), int((post_p == x).sum())
    da, db = local_density(pre_p, x), local_density(post_p, x)
    ra_, rb_ = sa/max(da,1e-9), sb/max(db,1e-9)
    ca, cb = int((pre_p == x-1).sum()), int((post_p == x-1).sum())
    spikes[x] = dict(pre_spike=sa, pre_ratio=float(ra_), pre_charm=ca,
                     post_spike=sb, post_ratio=float(rb_), post_charm=cb)
    print(f"{x:12,} | {sa:10,} {ra_:7.1f} {ca:5,} | {sb:11,} {rb_:7.1f} {cb:5,}")
print("\n  'ratio' = sales at exactly X, relative to non-round sales density nearby.")
print("  A notch at X should SUPPRESS the spike at X (it is taxed) and RAISE X-1.")

json.dump({"diff": {str(k): v for k, v in res.items()},
           "spikes": {str(k): v for k, v in spikes.items()}},
          open("diffbunch_results.json", "w"), indent=1)
print("\nwrote diffbunch_results.json")
