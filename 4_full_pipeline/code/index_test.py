"""Net out market appreciation with a repeat-sales index, then ask whether any
cash discount survives.

The raw comparison of cash-first against financed-first pairs conflates the
premium with however much the market moved over each pair's own holding window.
The fix is the standard Bailey-Muth-Nourse repeat-sales index: regress the log
price change of EVERY repeat pair on a set of borough-quarter dummies taking -1
at the first sale and +1 at the second. The fitted index is the market path; the
residual is the pair's excess return, purged of market movement.

The index is estimated on all pairs regardless of financing type, so it cannot
absorb the thing being tested.

Then, for pairs that switch financing type:
    cash -> financed : excess return should be POSITIVE if cash sales are cheap
    financed -> cash : excess return should be NEGATIVE by the same amount
A real premium is symmetric. Renovation is not.
"""
import gzip, csv, numpy as np, json, collections, datetime as dt
from estimate_pi import load

MIN_HOLD = 365


def q(d):
    return (d.year - 2016) * 4 + (d.month - 1) // 3


def pairs_all(rows, min_hold=MIN_HOLD):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["bbl"]].append(r)
    out = []
    for b, rs in by.items():
        rs = sorted(rs, key=lambda r: r["date"])
        for a, z in zip(rs, rs[1:]):
            da, dz = dt.date.fromisoformat(a["date"]), dt.date.fromisoformat(z["date"])
            if (dz - da).days < min_hold:
                continue
            out.append((a, z, (dz - da).days, da, dz))
    return out


rows = load()
P = pairs_all(rows)
print(f"repeat pairs, holding >= {MIN_HOLD} days: {len(P):,}")

# --- Bailey-Muth-Nourse index, per borough ---
boros = sorted({a["borough"] for a, z, g, da, dz in P})
nq = max(q(dz) for a, z, g, da, dz in P) + 1
cols = {(b, t): i for i, (b, t) in enumerate((b, t) for b in boros for t in range(nq))}
X = np.zeros((len(P), len(cols)))
y = np.array([np.log(float(z["price"])) - np.log(float(a["price"])) for a, z, g, da, dz in P])
for i, (a, z, g, da, dz) in enumerate(P):
    b = a["borough"]
    X[i, cols[(b, q(da))]] -= 1.0
    X[i, cols[(b, q(dz))]] += 1.0
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
resid = y - X @ beta
print(f"index estimated on all {len(P):,} pairs; R^2 = {1 - resid.var()/y.var():.3f}")
print(f"mean raw log change {y.mean():+.4f}, mean excess {resid.mean():+.4f}\n")

# --- split the excess return by transition direction ---
print("=" * 92)
print("EXCESS RETURN BY TRANSITION, market appreciation removed")
print("=" * 92)
print(f"{'transition':<26} {'pairs':>7} {'excess log change':>19} {'s.e.':>8} {'implied pi':>12}")
out = {}
groups = {"cash -> financed": [], "financed -> cash": [], "cash -> cash": [], "financed -> financed": []}
for i, (a, z, g, da, dz) in enumerate(P):
    ca, cz = 1 - int(a["financed_base"]), 1 - int(z["financed_base"])
    k = f"{'cash' if ca else 'financed'} -> {'cash' if cz else 'financed'}"
    groups[k].append(resid[i])
for k, v in groups.items():
    if len(v) < 100:
        print(f"{k:<26} {len(v):7,}   too few")
        continue
    v = np.array(v)
    mu, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
    pi = mu if k == "cash -> financed" else (-mu if k == "financed -> cash" else float("nan"))
    out[k] = dict(n=len(v), excess=float(mu), se=float(se), pi=None if np.isnan(pi) else float(pi))
    print(f"{k:<26} {len(v):7,} {mu:+19.4f} {se:8.4f} "
          f"{'' if np.isnan(pi) else f'{pi:12.4f}'}")

if "cash -> financed" in out and "financed -> cash" in out:
    a_, b_ = out["cash -> financed"], out["financed -> cash"]
    # symmetric estimate: half the gap in excess returns between the two directions
    pi_sym = (a_["excess"] - b_["excess"]) / 2
    se_sym = 0.5 * np.sqrt(a_["se"] ** 2 + b_["se"] ** 2)
    asym = a_["excess"] + b_["excess"]      # zero if symmetric
    se_as = np.sqrt(a_["se"] ** 2 + b_["se"] ** 2)
    print()
    print(f"   SYMMETRIC estimate of pi     : {pi_sym:+.4f}  s.e. {se_sym:.4f}  "
          f"95% CI [{pi_sym-1.96*se_sym:+.4f}, {pi_sym+1.96*se_sym:+.4f}]")
    print(f"   ASYMMETRY (should be zero)   : {asym:+.4f}  s.e. {se_as:.4f}  z = {asym/se_as:+.1f}")
    print()
    print("   The symmetric component is the most defensible reading of a certainty")
    print("   premium here. The asymmetric component cannot be a premium at all: it is")
    print("   whatever makes cash-first sequences different from financed-first ones,")
    print("   and renovation is the obvious candidate.")
    out["summary"] = dict(pi_symmetric=float(pi_sym), se=float(se_sym),
                          ci=[float(pi_sym-1.96*se_sym), float(pi_sym+1.96*se_sym)],
                          asymmetry=float(asym), asym_se=float(se_as))

json.dump(out, open("index_results.json", "w"), indent=1)
print("\nwrote index_results.json")
