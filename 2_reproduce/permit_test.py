"""The renovation test, done directly.

Section 4.3 identifies pi from the symmetric component of the cash->financed and
financed->cash excess returns, on the argument that improvement runs one way and
so shows up in the asymmetry. A referee objects, correctly, that if condition
also changes on the financed->cash side -- deterioration, estate liquidation --
then the two shocks cancel in the asymmetry while both survive in the symmetric
component, and an asymmetry of zero proves nothing.

This script answers the objection with data rather than argument. NYC Department
of Buildings permit issuance records every alteration permit by borough, block,
lot and date. For each repeat-sales pair we ask whether ANY A1/A2/NB/DM permit
was issued at that parcel between the two sales, and re-estimate on the pairs
where none was.

Limitation, stated plainly: a permit records permitted work. Unpermitted
cosmetic work is invisible here, so "permit-free" is a lower bound on
"unimproved", and the test bounds the renovation channel rather than eliminating
it.
"""
import numpy as np, json, gzip, csv, collections, datetime as dt
import gzip as _gz, csv as _csv

MIN_HOLD = 365


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
    return y, resid, 1 - (resid @ resid) / (y @ y)


BORO = {"MANHATTAN": 1, "BRONX": 2, "BROOKLYN": 3, "QUEENS": 4, "STATEN ISLAND": 5}

print("reading permits ...", flush=True)
perm = collections.defaultdict(list)
blockperm = collections.defaultdict(list)
n = bad = 0
with gzip.open("dob_permits.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        b = BORO.get((r["borough"] or "").strip().upper())
        try:
            blk, lot = int(r["block"]), int(r["lot"])
            d = dt.datetime.strptime(r["issuance_date"].strip(), "%m/%d/%Y").date()
        except Exception:
            bad += 1
            continue
        if not b:
            bad += 1
            continue
        if d.year < 2010:
            continue
        perm[f"{b}{blk:05d}{lot:04d}"].append(d)
        blockperm[f"{b}{blk:05d}"].append(d)
        n += 1
print(f"  {n:,} permits since 2010 on {len(perm):,} parcels ({bad:,} unusable rows)")
for k in perm:
    perm[k].sort()
for k in blockperm:
    blockperm[k].sort()


def has_permit(bbl, da, dz, block=False):
    v = (blockperm if block else perm).get(bbl[:6] if block else bbl)
    if not v:
        return False
    import bisect
    i = bisect.bisect_left(v, da)
    return i < len(v) and v[i] <= dz


def decompose(P, tag):
    y, resid, r2 = fit_index(P)
    kind = np.array([f"{'cash' if 1-int(a['financed_base']) else 'fin'}->"
                     f"{'cash' if 1-int(z['financed_base']) else 'fin'}"
                     for a, z, da, dz in P])
    A, B = resid[kind == "cash->fin"], resid[kind == "fin->cash"]
    if len(A) < 60 or len(B) < 60:
        print(f"  {tag}: too few switchers ({len(A)}, {len(B)})")
        return None
    pi = (A.mean() - B.mean()) / 2
    se = 0.5 * np.sqrt(A.var(ddof=1) / len(A) + B.var(ddof=1) / len(B))
    asym = A.mean() + B.mean()
    print(f"  {tag:<34} pairs {len(P):6,}  c->f {len(A):5,}  f->c {len(B):5,}  "
          f"pi {pi:+.4f} [{pi-1.96*se:+.4f},{pi+1.96*se:+.4f}]  A {asym:+.4f}")
    return dict(tag=tag, pairs=len(P), n_cf=len(A), n_fc=len(B), pi=float(pi),
                se=float(se), ci=[float(pi - 1.96 * se), float(pi + 1.96 * se)],
                asym=float(asym))


def load():
    with _gz.open("panel2.csv.gz", "rt", newline="") as fh:
        return list(_csv.DictReader(fh))


rows = load()
out = {}
for months in (36, 24):
    P = build_pairs(rows, int(months * 30.44))
    ph = [(a, z, da, dz) for a, z, da, dz in P if a["src"] == "house"]
    pc = [(a, z, da, dz) for a, z, da, dz in P if a["src"] == "condo"]
    print(f"\n=== min holding {months} months: {len(P):,} pairs "
          f"({len(ph):,} house, {len(pc):,} condo) ===")

    for name, PP in (("all", P), ("houses", ph), ("condos", pc), ("houses_blocklevel", ph)):
        if len(PP) < 800:
            continue
        blk = name in ("condos", "houses_blocklevel")
        flag = np.array([has_permit(a["bbl"], da, dz, blk) for a, z, da, dz in PP])
        kind = np.array([f"{'cash' if 1-int(a['financed_base']) else 'fin'}->"
                         f"{'cash' if 1-int(z['financed_base']) else 'fin'}"
                         for a, z, da, dz in PP])
        print(f"\n {name}: permit incidence between sales")
        for k in ("cash->fin", "fin->cash", "cash->cash", "fin->fin"):
            m = kind == k
            if m.sum() >= 60:
                print(f"    {k:<12} {m.sum():6,} pairs, {flag[m].mean()*100:5.1f}% with a permit")
        free = [p for p, f in zip(PP, flag) if not f]
        withp = [p for p, f in zip(PP, flag) if f]
        r = {}
        r["all"] = decompose(PP, f"{name}: all pairs")
        r["permit_free"] = decompose(free, f"{name}: NO permit between sales") if len(free) >= 800 else None
        r["permitted"] = decompose(withp, f"{name}: permit between sales") if len(withp) >= 800 else None
        r["incidence"] = {k: float((flag[kind == k]).mean()) for k in set(kind)
                          if (kind == k).sum() >= 60}
        r["incidence_n"] = {k: int((kind == k).sum()) for k in set(kind)
                            if (kind == k).sum() >= 60}
        out[f"{name}_{months}m"] = r

json.dump(out, open("permit_results.json", "w"), indent=1)
print("\nwrote permit_results.json")
