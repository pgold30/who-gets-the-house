"""Three additions to the Section 12 test.

1. Is the verdict robust to pi*? The decision rule is pi - pi* >= 0.117. Because
   pi* >= 0 by construction, the largest possible excess is pi itself. If pi is
   below the break-even, the test fails whatever pi* turns out to be - which
   removes the weakest link in the chain (HMDA denials are not fall-throughs)
   from the conclusion entirely.

2. Borough-level estimates. Section 12.1 argues a national average is not
   sufficient because the instrument in Section 8 triggers locally. The same
   argument applies inside a city.

3. Proper inference on the symmetric estimator: a parcel-clustered bootstrap
   rather than treating pairs as independent.
"""
import numpy as np, json, collections, datetime as dt
from estimate_pi import load

MIN_HOLD = int(36 * 30.44)          # the specification where the asymmetry vanishes
BREAKEVEN = 0.117
rng = np.random.default_rng(20260903)
BORO = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn", "4": "Queens", "5": "Staten Island"}


def q(d): return (d.year - 2016) * 4 + (d.month - 1) // 3


def build_pairs(rows, min_hold=MIN_HOLD, boro=None):
    by = collections.defaultdict(list)
    for r in rows:
        if boro and r["borough"] != boro:
            continue
        by[r["bbl"]].append(r)
    out = []
    for b, rs in by.items():
        rs = sorted(rs, key=lambda r: r["date"])
        for a, z in zip(rs, rs[1:]):
            da, dz = dt.date.fromisoformat(a["date"]), dt.date.fromisoformat(z["date"])
            if (dz - da).days >= min_hold:
                out.append((a, z, da, dz))
    return out


def excess(P):
    boros = sorted({a["borough"] for a, z, da, dz in P})
    nq = max(q(dz) for a, z, da, dz in P) + 1
    cols, j = {}, 0
    for b in boros:
        for t in range(1, nq):
            cols[(b, t)] = j; j += 1
    X = np.zeros((len(P), j))
    y = np.array([np.log(float(z["price"])) - np.log(float(a["price"])) for a, z, da, dz in P])
    for i, (a, z, da, dz) in enumerate(P):
        b = a["borough"]
        if (b, q(da)) in cols: X[i, cols[(b, q(da))]] -= 1.0
        if (b, q(dz)) in cols: X[i, cols[(b, q(dz))]] += 1.0
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def pi_sym(P, res):
    k = np.array([f"{'c' if 1-int(a['financed_base']) else 'f'}"
                  f"{'c' if 1-int(z['financed_base']) else 'f'}" for a, z, da, dz in P])
    A, B = res[k == "cf"], res[k == "fc"]
    if len(A) < 60 or len(B) < 60: return None
    return (A.mean() - B.mean()) / 2, len(A), len(B)


rows = load()
P = build_pairs(rows)
res = excess(P)
pt = pi_sym(P, res)

# --- parcel-clustered bootstrap ---
bbls = np.array([a["bbl"] for a, z, da, dz in P])
uniq = np.unique(bbls)
idx_by = {b: np.where(bbls == b)[0] for b in uniq}
draws = []
for _ in range(600):
    samp = rng.choice(uniq, size=len(uniq), replace=True)
    ii = np.concatenate([idx_by[b] for b in samp])
    Pb = [P[i] for i in ii]
    try:
        rb = excess(Pb); v = pi_sym(Pb, rb)
        if v: draws.append(v[0])
    except Exception:
        pass
draws = np.array(draws)
ci = np.percentile(draws, [2.5, 97.5])

print("=" * 86)
print(f"SYMMETRIC pi, holding >= 36 months, parcel-clustered bootstrap ({len(draws)} draws)")
print("=" * 86)
print(f"   pi      = {pt[0]:.4f}")
print(f"   95% CI  = [{ci[0]:.4f}, {ci[1]:.4f}]   (bootstrap s.e. {draws.std(ddof=1):.4f})")
print(f"   pairs   = {len(P):,}  ({pt[1]:,} cash->fin, {pt[2]:,} fin->cash)")

print()
print("=" * 86)
print("IS THE VERDICT ROBUST TO pi* ?")
print("=" * 86)
print(f"   decision rule      : reject H0 only if  pi - pi* >= {BREAKEVEN:.3f}")
print(f"   pi* >= 0 always, so the largest attainable excess is pi itself.")
print(f"   pi point estimate  : {pt[0]:.4f}  -> max excess {pt[0]:.4f} < {BREAKEVEN:.3f}  "
      f"=> FAILS at pi* = 0")
print(f"   pi upper 95% bound : {ci[1]:.4f}  -> max excess {ci[1]:.4f} "
      f"{'>=' if ci[1] >= BREAKEVEN else '<'} {BREAKEVEN:.3f}")
if ci[1] < BREAKEVEN:
    print("   => the test fails for EVERY non-negative pi*, even at the upper confidence")
    print("      bound of pi. The conclusion does not depend on pi* at all.")
else:
    need = pt[0] - BREAKEVEN
    print(f"   => clearing the break-even needs pi* <= {max(need,0):.4f} AND pi at its")
    print(f"      upper bound. Since Reher and Valkanov put pi* at 3.3-6.9% nationally,")
    print(f"      and NYC denial rates run 1.13x national, that is not available.")

print()
print("=" * 86)
print("BOROUGH-LEVEL ESTIMATES   (Section 12.1: the instrument triggers locally)")
print("=" * 86)
print(f"{'borough':<16} {'pairs':>7} {'cash->fin':>10} {'fin->cash':>10} {'pi':>9} {'max excess vs 0.117':>21}")
bor = {}
for b, name in BORO.items():
    Pb = build_pairs(rows, boro=b)
    if len(Pb) < 400: 
        print(f"{name:<16} {len(Pb):7,}   too few pairs"); continue
    rb = excess(Pb); v = pi_sym(Pb, rb)
    if not v:
        print(f"{name:<16} {len(Pb):7,}   too few switchers"); continue
    verdict = "clears" if v[0] >= BREAKEVEN else "fails"
    bor[name] = dict(pairs=len(Pb), pi=float(v[0]), cf=v[1], fc=v[2], verdict=verdict)
    print(f"{name:<16} {len(Pb):7,} {v[1]:10,} {v[2]:10,} {v[0]:9.4f} "
          f"{verdict:>21}")

json.dump({"pi": float(pt[0]), "ci_bootstrap": [float(ci[0]), float(ci[1])],
           "boot_se": float(draws.std(ddof=1)), "pairs": len(P),
           "breakeven": BREAKEVEN, "robust_to_pistar": bool(ci[1] < BREAKEVEN),
           "boroughs": bor}, open("finalize_results.json", "w"), indent=1)
print("\nwrote finalize_results.json")
