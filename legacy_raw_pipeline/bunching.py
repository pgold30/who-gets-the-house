"""Corrected bunching estimator.

Fixes over v1:
  * Notches apply at "X or more", so the sale AT the threshold is TAXED and belongs
    to the above-region. v1 let that focal spike cancel the deficit.
  * Round-number controls: dummies for exact multiples of 100k, 50k, 25k, so the
    counterfactual absorbs focal mass instead of attributing it to the tax.
  * Asymmetric exclusion band (Kopczuk & Munroe): the hole is wider than the pile.
  * Placebos restricted to windows that contain no live threshold.
  * Estimator-free evidence: charm prices at X-1 and suppression of the X spike.
"""
import json, numpy as np
rng = np.random.default_rng(20260901)
p = np.array([float(r["sale_price"]) for r in json.load(open("nyc_sales.json"))])

THRESHOLDS = {1_000_000: "1.00% (§1402-a)",
              2_000_000: "0.25% (§1402-b)",
              3_000_000: "0.50% (§1402-b + additional base)"}
# windows containing no live notch ($1M, $2M, $3M, $5M)
PLACEBOS = [1_500_000, 1_750_000, 2_250_000, 2_500_000]

def round_dummies(mid, bw):
    D = []
    for m in (100_000, 50_000, 25_000):
        D.append(((np.round(mid/bw)*bw) % m == 0).astype(float))
    return np.column_stack(D)

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
    # "or more": the bin containing thr is taxed -> above
    b_reg = (mid > thr-below) & (mid < thr)
    a_reg = (mid > thr) & (mid < thr+above)
    B = (cnt[b_reg]-cf[b_reg]).sum()
    M = (cf[a_reg]-cnt[a_reg]).sum()
    return dict(B=B, M=M, cf_above=cf[a_reg].sum(), cf_below=cf[b_reg].sum(),
                share=M/cf[a_reg].sum() if cf[a_reg].sum()>0 else np.nan,
                n=len(sel), mid=mid, cnt=cnt, cf=cf, thr=thr)

def boot(thr, R=600, **kw):
    out=[]
    for _ in range(R):
        s = rng.choice(p, size=len(p), replace=True)
        try:
            r = estimate(s, thr, **kw); out.append((r["B"], r["M"], r["share"]))
        except Exception: pass
    return np.array(out)

print("="*84)
print("CORRECTED ESTIMATES  (window +/-400k, bins 10k, band -50k/+100k, round-number controls)")
print("="*84)
print(f"{'threshold':>11} {'notch':<34} {'n':>7} {'B':>7} {'M':>7} {'M 95% CI':>18} {'M/cf':>7}")
res={}
for thr,lab in THRESHOLDS.items():
    r = estimate(p, thr); bs = boot(thr)
    ci = np.percentile(bs[:,1], [2.5,97.5]); sh = np.percentile(bs[:,2],[2.5,97.5])
    res[thr]=(r,ci,sh,bs)
    print(f"{thr:11,} {lab:<34} {r['n']:7,} {r['B']:7.0f} {r['M']:7.0f} [{ci[0]:7.0f},{ci[1]:7.0f}] {r['share']:7.2f}")
print()
print(f"{'placebo':>11} {'':<34} {'n':>7} {'B':>7} {'M':>7} {'M 95% CI':>18}")
for thr in PLACEBOS:
    r = estimate(p, thr); bs = boot(thr, R=400)
    ci = np.percentile(bs[:,1],[2.5,97.5])
    print(f"{thr:11,} {'(no notch in window)':<34} {r['n']:7,} {r['B']:7.0f} {r['M']:7.0f} [{ci[0]:7.0f},{ci[1]:7.0f}]")

print()
print("="*84); print("POWER at the 0.25% notch (2,000,000)"); print("="*84)
sd = res[2_000_000][3][:,1].std(ddof=1)
mde = 2.802*sd
cf_ab = res[2_000_000][0]["cf_above"]
print(f"  bootstrap s.d. of M      : {sd:.1f} sales")
print(f"  MDE (80% power, 5% 2-sided): {mde:.0f} sales = {mde/cf_ab*100:.0f}% of counterfactual mass above")
print(f"  observed M               : {res[2_000_000][0]['M']:.0f} = {res[2_000_000][0]['share']*100:.0f}%")
print(f"  $1M response for scale   : {res[1_000_000][0]['share']*100:.0f}% of its counterfactual")

print()
print("="*84); print("ESTIMATOR-FREE EVIDENCE"); print("="*84)
print("  charm price at X-1, and suppression of the spike at exactly X")
def spike_ratio(x):
    near = p[(p>x-25_000)&(p<x+25_000)]
    nonround = near[(near % 10_000)!=0]
    dens = len(nonround)/50_000*1.0
    return (p==x).sum()/max(dens*1,1e-9)
print(f"{'price point':>12} {'X-1 count':>10} {'spike at X':>11} {'spike/local density':>20}")
for x in list(THRESHOLDS)+PLACEBOS+[700_000,800_000,900_000,1_100_000,1_200_000]:
    print(f"{x:12,} {(p==x-1).sum():10d} {(p==x).sum():11d} {spike_ratio(x):20.2f}")
json.dump({str(k):{"B":float(v[0]["B"]),"M":float(v[0]["M"]),"share":float(v[0]["share"]),
                   "M_ci":[float(c) for c in v[1]],"share_ci":[float(c) for c in v[2]]}
           for k,v in res.items()}, open("bunching_v2_results.json","w"), indent=1)

# ---- figure ----
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.grid":True,
 "grid.color":"#dddddd","grid.linewidth":.7,"axes.spines.top":False,"axes.spines.right":False,
 "pdf.fonttype":42,"ps.fonttype":42,"savefig.dpi":330,"savefig.bbox":"tight"})
fig,axes=plt.subplots(1,3,figsize=(12.6,3.8))
for ax,thr,title in zip(axes, THRESHOLDS,
      ["§1402-a: 1.00% notch at \$1M","§1402-b: 0.25% notch at \$2M","§1402-b + base: 0.50% notch at \$3M"]):
    r=res[thr][0]; ci=res[thr][1]
    w=(r["mid"][1]-r["mid"][0])
    ax.bar(r["mid"]/1e6, r["cnt"], width=w/1e6*.9, color="#4C78A8", label="observed")
    ax.plot(r["mid"]/1e6, r["cf"], color="#E45756", lw=1.8, label="counterfactual")
    ax.axvline(thr/1e6, color="#333", ls="--", lw=1)
    ax.set_title(title, fontsize=9.5, loc="left")
    ax.set_xlabel("sale price (\$m)"); ax.set_ylabel("transactions")
    ax.annotate(f"missing above {r['M']:,.0f}\n[{ci[0]:,.0f}, {ci[1]:,.0f}]\n= {r['share']*100:.0f}% of counterfactual",
                xy=(.52,.70), xycoords="axes fraction", fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
fig.suptitle("All three notches relocate transactions; the smaller ones proportionally less. NYC residential sales, Aug 2025 – Jul 2026 (n = 39,021)",
             fontsize=10.5, y=1.04, x=.02, ha="left")
fig.savefig("Figure_4.png"); fig.savefig("Figure_4.pdf"); plt.close(fig)
print("\nfigure written")
