"""Repeat-sales index, properly identified, then the symmetry test.

Fixes over index_test.py: the borough-quarter dummy design is rank-deficient
(adding a constant within a borough cancels in the first difference), so the
first quarter of every borough is dropped as the base period. Residuals are then
centred and interpretable, and R^2 is reported against the uncentred total sum
of squares, which is the right benchmark for a no-intercept design.

Placebos added: pairs that do NOT switch financing type should show zero
asymmetry by construction, and a random relabelling of them should recover
nothing. If the "premium" shows up there too, it is not a premium.
"""
import numpy as np, json, collections, datetime as dt
from estimate_pi import load

MIN_HOLD = 365
rng = np.random.default_rng(20260903)


def q(d):
    return (d.year - 2016) * 4 + (d.month - 1) // 3


def build_pairs(rows, min_hold=MIN_HOLD):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["bbl"]].append(r)
    out = []
    for b, rs in by.items():
        rs = sorted(rs, key=lambda r: r["date"])
        for a, z in zip(rs, rs[1:]):
            da, dz = dt.date.fromisoformat(a["date"]), dt.date.fromisoformat(z["date"])
            if (dz - da).days >= min_hold:
                out.append((a, z, da, dz))
    return out


def fit_index(P):
    boros = sorted({a["borough"] for a, z, da, dz in P})
    nq = max(q(dz) for a, z, da, dz in P) + 1
    # drop quarter 0 of each borough as the base period -> identified
    cols, j = {}, 0
    for b in boros:
        for t in range(1, nq):
            cols[(b, t)] = j
            j += 1
    X = np.zeros((len(P), j))
    y = np.array([np.log(float(z["price"])) - np.log(float(a["price"])) for a, z, da, dz in P])
    for i, (a, z, da, dz) in enumerate(P):
        b = a["borough"]
        if (b, q(da)) in cols:
            X[i, cols[(b, q(da))]] -= 1.0
        if (b, q(dz)) in cols:
            X[i, cols[(b, q(dz))]] += 1.0
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    r2 = 1 - (resid @ resid) / (y @ y)
    return y, resid, r2


rows = load()
P = build_pairs(rows)
y, resid, r2 = fit_index(P)
print(f"repeat pairs (holding >= {MIN_HOLD}d): {len(P):,}")
print(f"index R^2 (uncentred) = {r2:.3f};  mean raw dlog {y.mean():+.4f}, "
      f"mean excess {resid.mean():+.4f}, sd {resid.std():.4f}\n")

kind = []
for a, z, da, dz in P:
    ca, cz = 1 - int(a["financed_base"]), 1 - int(z["financed_base"])
    kind.append(f"{'cash' if ca else 'fin'}->{'cash' if cz else 'fin'}")
kind = np.array(kind)

print("=" * 88)
print("EXCESS RETURN BY TRANSITION (market movement removed)")
print("=" * 88)
print(f"{'transition':<16} {'pairs':>7} {'excess':>10} {'s.e.':>8}")
st = {}
for k in ["cash->fin", "fin->cash", "cash->cash", "fin->fin"]:
    v = resid[kind == k]
    if len(v) < 100:
        continue
    mu, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
    st[k] = (mu, se, len(v))
    print(f"{k:<16} {len(v):7,} {mu:+10.4f} {se:8.4f}")

cf, fc = st["cash->fin"], st["fin->cash"]
pi_sym = (cf[0] - fc[0]) / 2
se_sym = 0.5 * np.sqrt(cf[1] ** 2 + fc[1] ** 2)
asym = cf[0] + fc[0]
se_as = np.sqrt(cf[1] ** 2 + fc[1] ** 2)
print()
print(f"   pi (symmetric component) : {pi_sym:+.4f}  s.e. {se_sym:.4f}  "
      f"95% CI [{pi_sym-1.96*se_sym:+.4f}, {pi_sym+1.96*se_sym:+.4f}]")
print(f"   asymmetry (should be 0)  : {asym:+.4f}  s.e. {se_as:.4f}  z = {asym/se_as:+.1f}")

print()
print("=" * 88)
print("PLACEBO   non-switching pairs, randomly relabelled as if they had switched")
print("=" * 88)
ns = resid[(kind == "cash->cash") | (kind == "fin->fin")]
draws = []
for _ in range(400):
    lab = rng.random(len(ns)) < 0.5
    a_, b_ = ns[lab], ns[~lab]
    draws.append((a_.mean() - b_.mean()) / 2)
draws = np.array(draws)
print(f"   placebo pi: mean {draws.mean():+.4f}, 95% range "
      f"[{np.percentile(draws,2.5):+.4f}, {np.percentile(draws,97.5):+.4f}]")
print(f"   observed pi {pi_sym:+.4f} sits {abs(pi_sym-draws.mean())/draws.std():.1f} "
      f"placebo s.d. from the placebo centre")

print()
print("=" * 88)
print("HOLDING-PERIOD SENSITIVITY of the symmetric estimate")
print("=" * 88)
print(f"{'min hold':<12} {'pairs':>8} {'pi_sym':>9} {'s.e.':>8} {'asymmetry':>11}")
sens = []
for months in [12, 24, 36, 48, 60]:
    Pm = build_pairs(rows, int(months * 30.44))
    if len(Pm) < 800:
        continue
    ym, rm, _ = fit_index(Pm)
    km = np.array([f"{'cash' if 1-int(a['financed_base']) else 'fin'}->"
                   f"{'cash' if 1-int(z['financed_base']) else 'fin'}" for a, z, da, dz in Pm])
    A, Bv = rm[km == "cash->fin"], rm[km == "fin->cash"]
    if len(A) < 100 or len(Bv) < 100:
        continue
    ps = (A.mean() - Bv.mean()) / 2
    ss = 0.5 * np.sqrt(A.var(ddof=1)/len(A) + Bv.var(ddof=1)/len(Bv))
    az = A.mean() + Bv.mean()
    sens.append(dict(months=months, pi=float(ps), se=float(ss), asym=float(az), pairs=len(Pm)))
    print(f"{'>= '+str(months)+'m':<12} {len(Pm):8,} {ps:+9.4f} {ss:8.4f} {az:+11.4f}")

json.dump({"transitions": {k: dict(excess=float(v[0]), se=float(v[1]), n=int(v[2]))
                           for k, v in st.items()},
           "pi_symmetric": float(pi_sym), "se": float(se_sym),
           "asymmetry": float(asym), "asym_se": float(se_as),
           "placebo_mean": float(draws.mean()), "placebo_sd": float(draws.std()),
           "holding_sensitivity": sens}, open("index2_results.json", "w"), indent=1)
print("\nwrote index2_results.json")
