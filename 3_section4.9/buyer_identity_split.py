"""Buyer-identity split on the paper's own four-borough panel.

Estimator functions are copied verbatim from the author's rerun_nosi.py, so the
"all pairs" row must reproduce the paper's 8,208 pairs at pi = 0.1114 exactly.
The only addition is a buyer flag: each sale in a repeat pair is matched to its
ACRIS deed, the deed's grantee is read from ACRIS Real Property Parties
(party_type '2'), and a pair is individual-to-individual when no grantee on
either deed is a business entity.

Retrieval is targeted rather than bulk: only the ~8,000 parcels that appear in
36-month house pairs are queried, batched by block, which is a few minutes
instead of the ~8M-row full legals pull.
"""
import gzip, csv, json, collections, datetime as dt, bisect, os, re, time
import urllib.parse, urllib.request
import os
import numpy as np

rng = np.random.default_rng(20260903)
SP = os.path.dirname(os.path.abspath(__file__))
S12 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2_reproduce")
DOM = "https://data.cityofnewyork.us/resource"
UA = {"User-Agent": "wgth-replication/1.0"}


def api(res, params, tries=6, timeout=180):
    url = f"{DOM}/{res}.json?" + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return json.load(r)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))


# ---------------------------------------------- author's estimator, verbatim
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


# ------------------------------------------------------------------- 1. panel
rows = [r for r in csv.DictReader(gzip.open(S12 + "/panel2.csv.gz", "rt", newline=""))
        if r["borough"] != "5"]
houses = [r for r in rows if r["src"] == "house"]
P36 = build(houses, int(36 * 30.44))
print(f"four-borough panel {len(rows):,} | houses {len(houses):,} | "
      f"36m pairs {len(P36):,}  (paper: 249,395 / 166,907 / 8,208)", flush=True)

# --------------------------------------------- 2. targeted legals, by block
CACHE = SP + "/deeds_for_pairs.json"
if os.path.exists(CACHE):
    deedmap = json.load(open(CACHE))
else:
    need_bbl = {s["bbl"] for p in P36 for s in p[:2]}
    blocks = collections.defaultdict(set)
    for b in need_bbl:
        blocks[b[0]].add(int(b[1:6]))
    print(f"parcels needed {len(need_bbl):,} across "
          f"{sum(len(v) for v in blocks.values()):,} blocks", flush=True)

    # A single 220-block chunk in Brooklyn holds ~118,000 legal rows, so a bare
    # $limit=50000 silently truncates and the parcels it drops are not random --
    # they are the dense, expensive blocks. Every chunk is therefore paged to
    # exhaustion on a document_id cursor, and the page size is asserted against
    # an exact count so a silent truncation cannot recur.
    PAGE = 50000
    legal = collections.defaultdict(set)          # bbl -> {document_id}
    for boro, blks in blocks.items():
        blks = sorted(blks); got = 0
        for i in range(0, len(blks), 220):
            chunk = ",".join(str(x) for x in blks[i:i + 220])
            base = (f"borough='{boro}' AND block in({chunk}) "
                    f"AND (document_id like '201%' OR document_id like '202%')")
            exact = int(api("8h5j-fqxa", {"$select": "count(1) AS n",
                                          "$where": base})[0]["n"])
            # Offset paging, not a document_id cursor: legals holds one row per
            # (document, parcel), so a multi-parcel document repeats its id and
            # a "document_id > last" cursor silently skips its remaining rows.
            # The assertion below caught exactly that, 50,460 of 50,621.
            seen = 0
            while seen < exact:
                page = api("8h5j-fqxa", {"$select": "document_id,block,lot",
                                         "$where": base,
                                         "$order": "document_id,block,lot",
                                         "$limit": PAGE, "$offset": seen})
                if not page:
                    break
                for L in page:
                    try:
                        bb = f"{boro}{int(L['block']):05d}{int(L['lot']):04d}"
                    except Exception:
                        continue
                    if bb in need_bbl:
                        legal[bb].add(L["document_id"])
                seen += len(page)
            assert seen >= exact * 0.999, f"truncated {boro} chunk {i}: {seen} of {exact}"
            got += seen
            print(f"\r  legals boro {boro}: {min(i+220,len(blks)):,}/{len(blks):,} blocks, "
                  f"{got:,} rows", end="", flush=True)
        print(flush=True)

    docids = sorted({d for v in legal.values() for d in v})
    print(f"  candidate documents {len(docids):,}; fetching DEED dates...", flush=True)
    ddate = {}
    for i in range(0, len(docids), 200):
        ids = ",".join("'" + x + "'" for x in docids[i:i + 200])
        for m in api("bnx9-e6tj", {"$select": "document_id,document_date",
                                   "$where": f"doc_type='DEED' AND document_id in({ids})",
                                   "$limit": 50000}):
            if m.get("document_date"):
                ddate[m["document_id"]] = m["document_date"][:10]
        if i % 4000 == 0:
            print(f"\r    {i:,}/{len(docids):,}", end="", flush=True)
    print(f"\r    {len(ddate):,} deeds dated", flush=True)
    deedmap = {bb: [[ddate[d], d] for d in v if d in ddate] for bb, v in legal.items()}
    json.dump(deedmap, open(CACHE, "w"))

# ---------------------------------------------------- 3. sale -> deed -> name
for p in P36:
    for s, sd in ((p[0], p[2]), (p[1], p[3])):
        best, bd = None, 46
        for ds, did in deedmap.get(s["bbl"], ()):
            g = abs((dt.date.fromisoformat(ds) - sd).days)
            if g < bd:
                best, bd = did, g
        s["deed"] = best
matched = sum(1 for p in P36 for s in p[:2] if s.get("deed"))
print(f"sales matched to a deed: {matched:,}/{2*len(P36):,} "
      f"({matched/(2*len(P36))*100:.1f}%)", flush=True)

GCACHE = SP + "/grantees_main.json"
if os.path.exists(GCACHE):
    gr = json.load(open(GCACHE))
else:
    need = sorted({s["deed"] for p in P36 for s in p[:2] if s.get("deed")})
    gr = collections.defaultdict(list)
    print(f"fetching grantees for {len(need):,} deeds...", flush=True)
    for i in range(0, len(need), 200):
        ids = ",".join("'" + x + "'" for x in need[i:i + 200])
        for x in api("636b-3b5g", {"$select": "document_id,name",
                                   "$where": f"party_type='2' AND document_id in({ids})",
                                   "$limit": 50000}):
            gr[x["document_id"]].append(x.get("name", ""))
        if i % 4000 == 0:
            print(f"\r  {i:,}/{len(need):,}", end="", flush=True)
    gr = dict(gr); json.dump(gr, open(GCACHE, "w"))
    print(f"\r  {len(gr):,} deeds with a grantee", flush=True)

BUSINESS = re.compile(
    r"\b(LLC|L\.?L\.?C|INC|CORP|CORPORATION|COMPANY|LP|L\.?P|LLP|LTD|"
    r"REALTY|PROPERTIES|HOLDINGS?|ASSOCIATES|PARTNERS\w*|VENTURES?|CAPITAL|"
    r"EQUITIES|GROUP|ENTERPRISES?|DEVELOPMENT|BUILDERS?|CONSTRUCTION|"
    r"MANAGEMENT|INVESTMENTS?|FUND|BANK|HOUSING|AUTHORITY)\b", re.I)


def biz(s):
    n = gr.get(s.get("deed") or "", [])
    return None if not n else any(BUSINESS.search(x.upper()) for x in n)


ind = np.array([biz(a) is False and biz(z) is False for a, z, _, _ in P36])
bus = np.array([biz(a) is True or biz(z) is True for a, z, _, _ in P36])
print(f"  individual-to-individual {ind.sum():,} | >=1 business {bus.sum():,}"
      f" | unresolved {(~(ind|bus)).sum():,}", flush=True)

# ----------------------------------------------------------------- 4. permits
BORO = {"MANHATTAN": 1, "BRONX": 2, "BROOKLYN": 3, "QUEENS": 4, "STATEN ISLAND": 5}
perm = collections.defaultdict(list)
with gzip.open(S12 + "/dob_permits.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        b = BORO.get((r["borough"] or "").strip().upper())
        try:
            blk, lot = int(r["block"]), int(r["lot"])
            dd = dt.datetime.strptime(r["issuance_date"].strip(), "%m/%d/%Y").date()
        except Exception:
            continue
        if not b or dd.year < 2010:
            continue
        perm[f"{b}{blk:05d}{lot:04d}"].append(dd)
for kk in perm:
    perm[kk].sort()


def hasp(bbl, da, dz):
    v = perm.get(bbl)
    if not v:
        return False
    i = bisect.bisect_left(v, da)
    return i < len(v) and v[i] <= dz


pf = np.array([not hasp(a["bbl"], da, dz) for a, z, da, dz in P36])
print(f"  permit-free pairs {pf.sum():,}  (paper: 6,316)", flush=True)

# ------------------------------------------------------------------ 5. splits
out = {}
print("\n" + "=" * 104)
print("  MAIN PANEL  |  four boroughs  |  houses  |  36-month filter")
print("=" * 104)
for tag, m in (("all pairs", np.ones(len(P36), bool)),
               ("individual to individual", ind),
               ("at least one business party", bus)):
    out[tag] = summ([P36[i] for i in np.where(m)[0]], tag)
print("\n  permit restriction applied on top:")
for tag, m in (("permit-free, all", pf),
               ("permit-free, individual to individual", pf & ind),
               ("permit-free, >=1 business party", pf & bus)):
    out[tag] = summ([P36[i] for i in np.where(m)[0]], tag)

json.dump(out, open(SP + "/split_main_results.json", "w"), indent=1)
print("\nwrote split_main_results.json")
