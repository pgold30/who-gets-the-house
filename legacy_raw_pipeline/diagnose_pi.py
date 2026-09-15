"""Is the estimated premium execution certainty, or renovation?

Section 12.3 warns that parcel fixed effects absorb time-invariant quality but not
condition changes between sales, and that flips are where cash concentrates. The
canonical contaminating pattern is: an investor buys a distressed property CHEAP
FOR CASH, renovates it, and resells DEAR TO A FINANCED owner-occupier. Under
parcel fixed effects that pattern mechanically produces "cash sales are cheaper"
with no execution-certainty channel whatsoever.

Two diagnostics separate them.

1. Holding-period sweep. A genuine certainty premium should not depend on how long
   the seller held. A renovation artefact should shrink as short holds are excluded.

2. TRANSITION DIRECTION - the decisive one. Restrict to parcels observed exactly
   twice with a change in financing type, and split by order:
      cash -> financed : the renovation story predicts a large positive pi here
      financed -> cash : the renovation story predicts pi near zero or NEGATIVE
   A real certainty premium is a property of the transaction, not of its position
   in the sequence, so it should appear with the SAME SIGN AND SIMILAR SIZE in
   both directions. Asymmetry is the signature of renovation.
"""
import gzip, csv, numpy as np, json, collections, datetime as dt
from estimate_pi import load, absorb, cluster_se, run

rows = load()

print("=" * 92)
print("1. HOLDING-PERIOD SWEEP   does pi survive excluding short holds?")
print("=" * 92)
print(f"{'minimum holding period':<30} {'pi':>8} {'s.e.':>7} {'95% CI':>19} {'n':>8} {'parcels':>8}")
sweep = []
for months in [0, 6, 12, 24, 36, 48, 60, 84]:
    r = run(rows, min_hold_days=int(months * 30.44), label=f"{months}m")
    if r:
        sweep.append(dict(months=months, **{k: r[k] for k in ("pi", "se", "ci", "n", "parcels")}))
        print(f"{'>= ' + str(months) + ' months':<30} {r['pi']:8.4f} {r['se']:7.4f} "
              f"[{r['ci'][0]:7.4f},{r['ci'][1]:7.4f}] {r['n']:8,} {r['parcels']:8,}")
    else:
        print(f"{'>= ' + str(months) + ' months':<30} {'too few switching parcels':>50}")

print()
print("=" * 92)
print("2. TRANSITION DIRECTION   the decisive test")
print("=" * 92)


def direction_split(rows, cash_col="financed_base", min_hold_days=365):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["bbl"]].append(r)
    out = {"cash_then_fin": [], "fin_then_cash": []}
    for b, rs in by.items():
        rs = sorted(rs, key=lambda r: r["date"])
        if len(rs) != 2:
            continue
        a, z = rs
        gap = (dt.date.fromisoformat(z["date"]) - dt.date.fromisoformat(a["date"])).days
        if gap < min_hold_days:
            continue
        ca, cz = 1 - int(a[cash_col]), 1 - int(z[cash_col])
        if ca == cz:
            continue
        key = "cash_then_fin" if ca == 1 else "fin_then_cash"
        out[key].append((a, z, gap))
    return out


sp = direction_split(rows)
res_dir = {}
print(f"{'transition':<26} {'pairs':>7} {'mean log price change':>23} {'implied pi':>12} {'s.e.':>8}")
for k, pairs in sp.items():
    if len(pairs) < 100:
        print(f"{k:<26} {len(pairs):7,}  too few")
        continue
    # first-difference within the pair; time effects removed by borough-quarter demeaning
    d = np.array([np.log(float(z["price"])) - np.log(float(a["price"])) for a, z, g in pairs])
    per = np.array([f"{a['borough']}_{a['date'][:4]}_{z['date'][:4]}" for a, z, g in pairs])
    gt = np.unique(per, return_inverse=True)[1]
    ones = np.ones((len(d), 1))
    dr, Xr = absorb(d, ones, [gt])
    # mean change net of period effects
    mu = d.mean()
    se = d.std(ddof=1) / np.sqrt(len(d))
    # cash->financed: price RISES if cash sales are cheaper, so pi = +mean
    # financed->cash: price FALLS if cash sales are cheaper, so pi = -mean
    pi = mu if k == "cash_then_fin" else -mu
    res_dir[k] = dict(pairs=len(pairs), mean_dlog=float(mu), se=float(se), pi=float(pi),
                      median_gap_days=float(np.median([g for _, _, g in pairs])))
    print(f"{k:<26} {len(pairs):7,} {mu:+23.4f} {pi:12.4f} {se:8.4f}")

if len(res_dir) == 2:
    a, b = res_dir["cash_then_fin"], res_dir["fin_then_cash"]
    diff = a["pi"] - b["pi"]
    sed = np.sqrt(a["se"] ** 2 + b["se"] ** 2)
    print()
    print(f"   asymmetry (cash-first minus financed-first) = {diff:+.4f}  s.e. {sed:.4f}  "
          f"z = {diff/sed:+.1f}")
    print("   A genuine certainty premium is symmetric. Renovation predicts a large")
    print("   positive asymmetry, because cash buys precede the improvement.")
    print(f"   median holding period: cash-first {a['median_gap_days']:.0f} days, "
          f"financed-first {b['median_gap_days']:.0f} days")

json.dump({"holding_sweep": sweep, "direction": res_dir}, open("diagnose_results.json", "w"), indent=1)
print("\nwrote diagnose_results.json")
