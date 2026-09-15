"""Merge the recovered condominium sales into the panel and re-run Section 12."""
import json, gzip, csv, collections, numpy as np, datetime as dt

# ---- merge ----
rows = []
with gzip.open("panel.csv.gz", "rt", newline="") as fh:
    for r in csv.DictReader(fh):
        r["src"] = "house"
        rows.append(r)
n_house = len(rows)
for r in json.load(open("condo_rows.json")):
    rows.append({k: str(v) for k, v in r.items()})
print(f"houses {n_house:,} + condos {len(rows)-n_house:,} = {len(rows):,}")

rows.sort(key=lambda r: (r["bbl"], r["date"]))
cnt = collections.Counter(r["bbl"] for r in rows)
seq = collections.Counter()
for r in rows:
    seq[r["bbl"]] += 1
    r["n_sale"], r["n_sales_total"] = seq[r["bbl"]], cnt[r["bbl"]]
    r.setdefault("mort_amt", "0")
cols = ["bbl", "date", "price", "borough", "src", "financed_strict", "financed_base",
        "financed_wide", "mort_amt", "n_sale", "n_sales_total"]
with gzip.open("panel2.csv.gz", "wt", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
print(f"wrote panel2.csv.gz")

# ---- rerun ----
MIN_HOLD, BREAKEVEN = int(36 * 30.44), 0.117
PS_LO, PS_HI = 0.0374, 0.0781
rng = np.random.default_rng(20260903)
BORO = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn", "4": "Queens", "5": "Staten Island"}


def q(d): return (d.year - 2016) * 4 + (d.month - 1) // 3


def build(rows, min_hold=MIN_HOLD, boro=None, src=None):
    by = collections.defaultdict(list)
    for r in rows:
        if boro and r["borough"] != boro: continue
        if src and r["src"] != src: continue
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
    bs = sorted({a["borough"] for a, z, da, dz in P})
    nq = max(q(dz) for a, z, da, dz in P) + 1
    cols, j = {}, 0
    for b in bs:
        for t in range(1, nq):
            cols[(b, t)] = j; j += 1
    X = np.zeros((len(P), j))
    y = np.array([np.log(float(z["price"])) - np.log(float(a["price"])) for a, z, da, dz in P])
    for i, (a, z, da, dz) in enumerate(P):
        b = a["borough"]
        if (b, q(da)) in cols: X[i, cols[(b, q(da))]] -= 1
        if (b, q(dz)) in cols: X[i, cols[(b, q(dz))]] += 1
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def pisym(P, res):
    k = np.array([f"{'c' if 1-int(a['financed_base']) else 'f'}"
                  f"{'c' if 1-int(z['financed_base']) else 'f'}" for a, z, da, dz in P])
    A, B = res[k == "cf"], res[k == "fc"]
    if len(A) < 60 or len(B) < 60: return None
    return (A.mean() - B.mean()) / 2, len(A), len(B), (A.mean() + B.mean())


def boot(P, R=400):
    bb = np.array([a["bbl"] for a, z, da, dz in P])
    u = np.unique(bb); idx = {x: np.where(bb == x)[0] for x in u}
    out = []
    for _ in range(R):
        s = rng.choice(u, size=len(u), replace=True)
        ii = np.concatenate([idx[x] for x in s])
        Pb = [P[i] for i in ii]
        try:
            v = pisym(Pb, excess(Pb))
            if v: out.append(v[0])
        except Exception: pass
    return np.percentile(out, [2.5, 97.5]) if out else (np.nan, np.nan)


def verdict(ci):
    lo, hi = ci[0] - PS_HI, ci[1] - PS_LO
    return "CLEARS" if lo >= BREAKEVEN else ("fails" if hi < BREAKEVEN else "ambiguous"), lo, hi


print("\n" + "=" * 98)
print("SECTION 12, HOUSES + CONDOMINIUMS   holding >= 36 months")
print("=" * 98)
print(f"{'market':<18} {'pairs':>7} {'switch':>7} {'pi':>8} {'95% CI':>20} {'asym':>8} "
      f"{'excess range':>18} {'verdict':>10}")
res = {}
for name, kw in [("New York City", {})] + [(v, {"boro": k}) for k, v in BORO.items()]:
    P = build(rows, **kw)
    if len(P) < 400:
        print(f"{name:<18} {len(P):7,}   too few pairs"); continue
    v = pisym(P, excess(P))
    if not v:
        print(f"{name:<18} {len(P):7,}   too few switching parcels"); continue
    ci = boot(P)
    vd, lo, hi = verdict(ci)
    res[name] = dict(pairs=len(P), switch=v[1]+v[2], pi=float(v[0]),
                     ci=[float(ci[0]), float(ci[1])], asym=float(v[3]),
                     excess=[float(lo), float(hi)], verdict=vd)
    print(f"{name:<18} {len(P):7,} {v[1]+v[2]:7,} {v[0]:8.4f} [{ci[0]:8.4f},{ci[1]:7.4f}] "
          f"{v[3]:+8.4f} [{lo:8.4f},{hi:7.4f}] {vd:>10}")

print("\n" + "=" * 98)
print("BY PROPERTY TYPE")
print("=" * 98)
for src in ["house", "condo"]:
    P = build(rows, src=src)
    if len(P) < 400: continue
    v = pisym(P, excess(P))
    if not v: continue
    ci = boot(P)
    vd, lo, hi = verdict(ci)
    res[src] = dict(pairs=len(P), pi=float(v[0]), ci=[float(ci[0]), float(ci[1])],
                    asym=float(v[3]), excess=[float(lo), float(hi)], verdict=vd)
    print(f"{src:<18} {len(P):7,} {v[1]+v[2]:7,} {v[0]:8.4f} [{ci[0]:8.4f},{ci[1]:7.4f}] "
          f"{v[3]:+8.4f} [{lo:8.4f},{hi:7.4f}] {vd:>10}")

json.dump(res, open("merged_results.json", "w"), indent=1)
print("\nwrote merged_results.json")
