"""Shared estimator, copied verbatim from the author's rerun_nosi.py.

Kept in one place so every script in this directory uses identical code and the
"all pairs" rows must reproduce the paper. Previously each script exec()'d
another's source, which broke the moment a file was renamed.
"""
import collections, datetime as dt
import numpy as np

rng = np.random.default_rng(20260903)

def q(d): return (d.year - 2016) * 4 + (d.month - 1) // 3


def build(rows, mh=1096):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["bbl"]].append(r)
    out = []
    for b, rs in by.items():
        rs = sorted(rs, key=lambda r: r["date"])
        for a, z in zip(rs, rs[1:]):
            da, dz = dt.date.fromisoformat(a["date"]), dt.date.fromisoformat(z["date"])
            if (dz - da).days >= mh:
                out.append((a, z, da, dz))
    return out


def excess(P):
    bs = sorted({a["borough"] for a, z, _, _ in P}); nq = max(q(dz) for _, _, _, dz in P) + 1
    cols = {}; j = 0
    for b in bs:
        for t in range(1, nq):
            cols[(b, t)] = j; j += 1
    X = np.zeros((len(P), j))
    y = np.array([np.log(float(z["price"])) - np.log(float(a["price"])) for a, z, _, _ in P])
    for i, (a, z, da, dz) in enumerate(P):
        b = a["borough"]
        if (b, q(da)) in cols: X[i, cols[(b, q(da))]] -= 1
        if (b, q(dz)) in cols: X[i, cols[(b, q(dz))]] += 1
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def kinds(P):
    return np.array([f"{'cash' if 1-int(a['financed_base']) else 'fin'}->"
                     f"{'cash' if 1-int(z['financed_base']) else 'fin'}"
                     for a, z, _, _ in P])


def pisym(P, r, minn=60):
    k = kinds(P); A, B = r[k == "cash->fin"], r[k == "fin->cash"]
    if len(A) < minn or len(B) < minn:
        return None, len(A), len(B)
    return (A.mean() - B.mean()) / 2, len(A), len(B)


def boot(P, n=400):
    par = collections.defaultdict(list)
    for i, (a, z, _, _) in enumerate(P):
        par[a["bbl"]].append(i)
    keys = list(par); out = []
    for _ in range(n):
        idx = []
        for kk in rng.choice(len(keys), len(keys), replace=True):
            idx += par[keys[kk]]
        Pb = [P[i] for i in idx]
        try:
            v = pisym(Pb, excess(Pb))[0]
            if v is not None:
                out.append(v)
        except Exception:
            pass
    return np.percentile(out, [2.5, 97.5]) if len(out) > 30 else (np.nan, np.nan)


def summ(P, tag, bs=True):
    if len(P) < 300:
        print(f"  {tag:<42} {len(P):6,}  too few pairs"); return None
    r = excess(P); v = pisym(P, r)
    if v[0] is None:
        print(f"  {tag:<42} {len(P):6,}  too few switchers (cf {v[1]}, fc {v[2]})"); return None
    pi, cf, fc = v
    k = kinds(P); A, B = r[k == "cash->fin"], r[k == "fin->cash"]
    asym = A.mean() + B.mean()
    ci = boot(P) if bs else (np.nan, np.nan)
    print(f"  {tag:<42} {len(P):6,} cf {cf:5,} fc {fc:5,}  pi {pi:+.4f} "
          f"[{ci[0]:+.4f},{ci[1]:+.4f}]  A {asym:+.4f}", flush=True)
    return dict(pairs=len(P), cf=int(cf), fc=int(fc), pi=float(pi),
                ci=[float(ci[0]), float(ci[1])], asym=float(asym))


def load_panel(s12_dir):
    """The four-borough house panel and its 36-month repeat pairs."""
    import csv, gzip, os
    rows = [r for r in csv.DictReader(
                gzip.open(os.path.join(s12_dir, "panel2.csv.gz"), "rt", newline=""))
            if r["borough"] != "5"]
    return rows, build([r for r in rows if r["src"] == "house"], int(36 * 30.44))


def load_permits(s12_dir):
    """bbl -> sorted issuance dates, and a has-permit-between predicate."""
    import csv, gzip, os, bisect
    BORO = {"MANHATTAN": 1, "BRONX": 2, "BROOKLYN": 3, "QUEENS": 4,
            "STATEN ISLAND": 5}
    perm = collections.defaultdict(list)
    with gzip.open(os.path.join(s12_dir, "dob_permits.csv.gz"), "rt") as fh:
        for r in csv.DictReader(fh):
            b = BORO.get((r["borough"] or "").strip().upper())
            try:
                blk, lot = int(r["block"]), int(r["lot"])
                d = dt.datetime.strptime(r["issuance_date"].strip(), "%m/%d/%Y").date()
            except Exception:
                continue
            if b and d.year >= 2010:
                perm[f"{b}{blk:05d}{lot:04d}"].append(d)
    for k in perm:
        perm[k].sort()

    def has_permit(bbl, da, dz):
        v = perm.get(bbl)
        if not v:
            return False
        i = bisect.bisect_left(v, da)
        return i < len(v) and v[i] <= dz
    return has_permit
