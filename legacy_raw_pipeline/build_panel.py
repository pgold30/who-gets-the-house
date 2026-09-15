"""Build the repeat-sales panel with a financing indicator, for the Section 12
break-even test.

Inputs
  /home/claude/empirical_c6/sample_2016_2025.json   431,471 NYC DOF residential
      sales 2016-2025 (BBL, price, date), the C6 analysis sample
  acris_master.csv.gz, acris_legals_*.csv.gz        ACRIS deeds and mortgages

Method
  A purchase is classified FINANCED if a mortgage (doc_type MTGE) is recorded
  against the same BBL within a window around the sale date, and CASH otherwise.
  The window is asymmetric and configurable: purchase-money mortgages are
  normally recorded with or shortly after the deed, so the default is
  [-15, +90] days. Two robustness variants are computed:

    strict    [-15, +30]   fewer false FINANCED, more false CASH
    wide      [-15, +180]  catches recording lag, risks absorbing cash-out refis

  The wide window is where delayed financing bites: a genuine cash purchase
  refinanced inside 90 days is misclassified as financed, which attenuates the
  estimated premium. The strict window has the opposite bias. Reporting all
  three is the only honest option, since neither bound is obviously right.

Output
  panel.csv.gz  one row per sale: bbl, date, price, cash flags, sale sequence
"""
import json, gzip, csv, collections, datetime as dt, glob, sys

SALES = "/home/claude/empirical_c6/sample_2016_2025.json"
WINDOWS = {"strict": (-15, 30), "base": (-15, 90), "wide": (-15, 180)}

# Sample restriction, and why it is a restriction of necessity rather than convenience.
#
# CO-OPS (categories 09, 10, 17) are excluded because a co-operative share loan is
# a security interest in personalty, perfected by UCC filing, and never appears in
# ACRIS as a mortgage against the parcel. Measured "financed" share for co-ops is
# 1-3%, which is an artefact of that statutory fact, not a cash market. This is the
# same Article 11 / Article 31 gap the paper discusses for the mortgage recording tax.
#
# CONDOMINIUMS (04, 12, 13, 15) are excluded because DOF bills a condominium unit
# under a billing lot in the 7501+ range while ACRIS records instruments against the
# unit lots (1001, 1002, ...), so the two BBLs never join. Measured financed share is
# 0.0%. Recovering condominiums needs a PLUTO condominium crosswalk; it is feasible
# and is left as an extension.
#
# What remains is 1-3 family dwellings, where the DOF and ACRIS parcel identifiers
# agree and the financed share (54-73%) is plausible. These are also the segment in
# which the owner-occupier / institution competition the paper models actually occurs.
KEEP_CODES = {"01", "02", "03"}


def d(s):
    return dt.date.fromisoformat(s[:10])


def load_legals():
    """document_id -> bbl (10-char). Documents touching several lots are dropped:
    a mortgage spanning multiple parcels cannot be attributed to one sale."""
    m, multi = {}, set()
    for f in sorted(glob.glob("acris_legals.csv.gz")):
        with gzip.open(f, "rt", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    bbl = f"{int(r['borough'])}{int(r['block']):05d}{int(r['lot']):04d}"
                except (ValueError, TypeError, KeyError):
                    continue
                did = r["document_id"]
                if did in m and m[did] != bbl:
                    multi.add(did)
                else:
                    m[did] = bbl
        print(f"   legals {f}: cumulative {len(m):,} docs", flush=True)
    for did in multi:
        m.pop(did, None)
    print(f"   dropped {len(multi):,} multi-parcel documents", flush=True)
    return m


def load_master():
    """document_id -> (doc_type, date, amount). Uses document_date where present,
    falling back to the recording date."""
    out = {}
    with gzip.open("acris_master.csv.gz", "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            ds = r.get("document_date") or r.get("recorded_datetime") or ""
            if len(ds) < 10:
                continue
            try:
                amt = float(r.get("document_amt") or 0)
            except ValueError:
                amt = 0.0
            out[r["document_id"]] = (r["doc_type"], ds[:10], amt)
    print(f"   master: {len(out):,} documents", flush=True)
    return out


def main():
    legals, master = load_legals(), load_master()

    # mortgages by bbl, sorted by date
    mort = collections.defaultdict(list)
    for did, (dtp, ds, amt) in master.items():
        if dtp != "MTGE":
            continue
        b = legals.get(did)
        if b:
            mort[b].append((d(ds), amt))
    for b in mort:
        mort[b].sort()
    print(f"   mortgages matched to a single parcel: "
          f"{sum(len(v) for v in mort.values()):,} across {len(mort):,} parcels", flush=True)

    sales = json.load(open(SALES))
    rows, seq = [], collections.Counter()
    dropped = collections.Counter()
    for s in sales:
        b = str(s.get("bbl") or "")
        if len(b) != 10:
            dropped["no usable BBL"] += 1
            continue
        cat = (s.get("building_class_category") or "").strip()
        if cat[:2] not in KEEP_CODES:
            dropped["not 1-3 family (co-op / condo / other)"] += 1
            continue
        sd = d(s["sale_date"])
        rec = {"bbl": b, "date": sd.isoformat(), "price": float(s["sale_price"]),
               "borough": b[0]}
        ms = mort.get(b, [])
        for name, (lo, hi) in WINDOWS.items():
            a, z = sd + dt.timedelta(days=lo), sd + dt.timedelta(days=hi)
            hit = [amt for md, amt in ms if a <= md <= z]
            rec[f"financed_{name}"] = int(bool(hit))
            if name == "base":
                rec["mort_amt"] = max(hit) if hit else 0.0
        rows.append(rec)

    rows.sort(key=lambda r: (r["bbl"], r["date"]))
    for r in rows:
        seq[r["bbl"]] += 1
        r["n_sale"] = seq[r["bbl"]]
    counts = collections.Counter(r["bbl"] for r in rows)
    for r in rows:
        r["n_sales_total"] = counts[r["bbl"]]

    with gzip.open("panel.csv.gz", "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    for k, v in dropped.items():
        print(f"   dropped, {k}: {v:,}")
    rep = sum(1 for r in rows if r["n_sales_total"] >= 2)
    print(f"\n   sales with a usable BBL : {len(rows):,}")
    for name in WINDOWS:
        c = sum(1 for r in rows if not r[f"financed_{name}"])
        print(f"   cash share ({name:6}) : {c/len(rows)*100:5.1f}%")
    print(f"   sales on repeat-sale parcels : {rep:,} "
          f"({len(set(r['bbl'] for r in rows if r['n_sales_total']>=2)):,} parcels)")


if __name__ == "__main__":
    main()
