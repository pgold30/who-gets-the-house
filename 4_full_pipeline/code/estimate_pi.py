"""Estimate the execution-certainty premium pi on NYC repeat sales.

Implements equation (7) of Section 12.4:

    log P_imt = pi * Cash_imt + gamma_i + delta_mt + X'_imt beta + eps_imt

gamma_i are parcel fixed effects, delta_mt market-by-period effects (borough x
calendar quarter). The coefficient on Cash is -pi: cash buyers pay less, and the
gap is the premium a seller forgoes for certainty of closing. Identification
comes from parcels that transact more than once with variation in financing
type, exactly as Section 12.3 specifies.

Both fixed effects are absorbed by alternating projections, then OLS on the
residualised variables. Standard errors are clustered on the parcel.

Section 12.3's warning governs the whole exercise: cash buyers are not randomly
assigned, they concentrate in distressed and defective properties, and a naive
estimate overstates pi in the direction that flatters the paper's conclusion.
Parcel fixed effects absorb time-invariant quality but NOT condition changes
between sales, which is why renovation flips are excluded and the holding-period
threshold is swept rather than fixed.
"""
import gzip, csv, numpy as np, json, collections, datetime as dt, itertools

PANEL = "panel.csv.gz"


def load():
    rows = []
    with gzip.open(PANEL, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    return rows


def absorb(y, X, groups, iters=60, tol=1e-10):
    """Alternating projections: demean y and each column of X within every
    grouping in `groups` until convergence."""
    def dm(v):
        v = v.copy()
        for _ in range(iters):
            before = v.copy()
            for g in groups:
                s = np.bincount(g, weights=v)
                n = np.bincount(g)
                v -= (s / np.maximum(n, 1))[g]
            if np.max(np.abs(v - before)) < tol:
                break
        return v
    return dm(y), np.column_stack([dm(X[:, j]) for j in range(X.shape[1])])


def cluster_se(Xr, resid, cid, k_absorbed):
    n, k = Xr.shape
    XtX_inv = np.linalg.pinv(Xr.T @ Xr)
    meat = np.zeros((k, k))
    order = np.argsort(cid)
    Xs, rs, cs = Xr[order], resid[order], cid[order]
    start = 0
    for i in range(1, len(cs) + 1):
        if i == len(cs) or cs[i] != cs[start]:
            xg, rg = Xs[start:i], rs[start:i]
            u = xg.T @ rg
            meat += np.outer(u, u)
            start = i
    G = len(np.unique(cid))
    dof = (G / (G - 1)) * ((n - 1) / max(n - k - k_absorbed, 1))
    V = XtX_inv @ meat @ XtX_inv * dof
    return np.sqrt(np.diag(V)), G


def run(rows, cash_col="financed_base", min_hold_days=365, max_hold_days=None,
        trim=0.01, label=""):
    # repeat-sale parcels only
    by = collections.defaultdict(list)
    for r in rows:
        by[r["bbl"]].append(r)
    recs = []
    for b, rs in by.items():
        if len(rs) < 2:
            continue
        rs = sorted(rs, key=lambda r: r["date"])
        # holding-period filter applied pairwise: drop a sale whose gap to the
        # previous sale on the same parcel is shorter than min_hold_days (flips)
        keep = [rs[0]]
        for prev, cur in zip(rs, rs[1:]):
            gap = (dt.date.fromisoformat(cur["date"]) - dt.date.fromisoformat(prev["date"])).days
            if gap >= min_hold_days and (max_hold_days is None or gap <= max_hold_days):
                keep.append(cur)
        if len(keep) < 2:
            continue
        recs += keep
    if len(recs) < 500:
        return None

    y = np.log(np.array([float(r["price"]) for r in recs]))
    cash = np.array([1.0 - float(r[cash_col]) for r in recs])
    bbl = np.array([r["bbl"] for r in recs])
    date = [dt.date.fromisoformat(r["date"]) for r in recs]
    boro = np.array([r["borough"] for r in recs])
    per = np.array([f"{b}_{d.year}Q{(d.month-1)//3+1}" for b, d in zip(boro, date)])

    # trim extreme log prices
    if trim:
        lo, hi = np.quantile(y, [trim, 1 - trim])
        m = (y >= lo) & (y <= hi)
        y, cash, bbl, per = y[m], cash[m], bbl[m], per[m]
        recs = [r for r, k in zip(recs, m) if k]

    gp = np.unique(bbl, return_inverse=True)[1]
    gt = np.unique(per, return_inverse=True)[1]
    # keep only parcels that still have >=2 sales and vary in cash
    cnt = np.bincount(gp)
    varies = np.zeros(len(cnt), bool)
    for i in range(len(cash)):
        pass
    sums = np.bincount(gp, weights=cash)
    varies = (sums > 0) & (sums < cnt)
    m = (cnt[gp] >= 2) & varies[gp]
    if m.sum() < 300:
        return None
    y, cash, bbl, per = y[m], cash[m], bbl[m], per[m]
    gp = np.unique(bbl, return_inverse=True)[1]
    gt = np.unique(per, return_inverse=True)[1]

    X = cash.reshape(-1, 1)
    yr, Xr = absorb(y, X, [gp, gt])
    beta = np.linalg.lstsq(Xr, yr, rcond=None)[0]
    resid = yr - Xr @ beta
    se, G = cluster_se(Xr, resid, gp, len(np.unique(gp)) + len(np.unique(gt)))
    pi = -beta[0]
    return dict(label=label, pi=float(pi), se=float(se[0]),
                ci=[float(pi - 1.96 * se[0]), float(pi + 1.96 * se[0])],
                n=int(len(y)), parcels=int(G),
                cash_share=float(cash.mean()))


if __name__ == "__main__":
    rows = load()
    print(f"panel rows: {len(rows):,}\n")
    print("=" * 88)
    print("pi = execution-certainty premium (proportional discount accepted from a cash buyer)")
    print("=" * 88)
    print(f"{'specification':<42} {'pi':>8} {'s.e.':>7} {'95% CI':>18} {'n':>8} {'parcels':>8}")
    out = []
    specs = [
        ("base window, flips >12m excluded", dict(cash_col="financed_base", min_hold_days=365)),
        ("strict window (-15,+30d)",         dict(cash_col="financed_strict", min_hold_days=365)),
        ("wide window (-15,+180d)",          dict(cash_col="financed_wide", min_hold_days=365)),
        ("no flip filter",                   dict(cash_col="financed_base", min_hold_days=0)),
        ("flips >24m excluded",              dict(cash_col="financed_base", min_hold_days=730)),
        ("flips >36m excluded",              dict(cash_col="financed_base", min_hold_days=1095)),
        ("no price trim",                    dict(cash_col="financed_base", min_hold_days=365, trim=0)),
    ]
    for lab, kw in specs:
        r = run(rows, label=lab, **kw)
        if r:
            out.append(r)
            print(f"{lab:<42} {r['pi']:8.4f} {r['se']:7.4f} "
                  f"[{r['ci'][0]:7.4f},{r['ci'][1]:7.4f}] {r['n']:8,} {r['parcels']:8,}")
        else:
            print(f"{lab:<42} {'insufficient variation':>50}")
    json.dump(out, open("pi_results.json", "w"), indent=1)
    print("\nwrote pi_results.json")
