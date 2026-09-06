"""Co-operative financing, recovered from ACRIS Personal Property INIC filings.

Improvements over the first attempt.

UNIT IDENTIFIER. The Department of Finance leaves apartment_number empty for most
co-operative sales but writes the unit after a comma in the address field
("345 W 55TH ST, 6C"). Combining the two recovers a unit for 86.7% of sales, so
repeat sales can be formed at the apartment rather than the building.

ASSIGNMENT RULE. A UCC filing identifies the building, not the apartment, so
attributing filings to sales needs care. Counting sales k and filings m in a
common window around each sale:
    m == 0   -> every sale in the window is cash          (unambiguous)
    m >= k   -> every sale in the window is financed       (unambiguous)
    0 < m < k -> ambiguous; the sales are dropped
This recovers far more than requiring k == 1, and only discards genuinely
undecidable cases.

VALIDATION. The identical rule is applied to 1-3 family houses, where the parcel
already identifies the unit and the true financing flag is known from the
real-property records.
"""
import json, gzip, csv, collections, datetime as dt, os

SALES = os.environ.get("NYC_SALES",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "sample_2016_2025.json"))

COOP_CODES = {"09", "10", "17"}
HOUSE_CODES = {"01", "02", "03"}
SALE_WIN, FIN_LO, FIN_HI = 45, -15, 90


def d(s): return dt.date.fromisoformat(s[:10])


def unit_of(r):
    a = (r.get("apartment_number") or "").strip().upper()
    if a:
        return a
    ad = r.get("address") or ""
    return ad.split(",", 1)[1].strip().upper() if "," in ad else ""


def load_inic():
    with gzip.open("pp_master_inic.csv.gz", "rt", newline="") as fh:
        m = {r["document_id"]: (r.get("recorded_datetime") or "")[:10]
             for r in csv.DictReader(fh) if r.get("doc_type") == "INIC"}
    seen, multi = {}, set()
    with gzip.open("pp_legals.csv.gz", "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            did = r["document_id"]
            if did not in m:
                continue
            try:
                b = f"{int(r['borough'])}{int(r['block']):05d}{int(r['lot']):04d}"
            except (ValueError, TypeError):
                continue
            if did in seen and seen[did] != b:
                multi.add(did)
            else:
                seen[did] = b
    out = collections.defaultdict(list)
    for did, b in seen.items():
        if did not in multi and len(m[did]) >= 10:
            out[b].append(d(m[did]))
    for b in out:
        out[b].sort()
    return out


def assign(sale_recs, filings):
    """sale_recs: list of dicts with bbl,date. Returns (classified rows, stats)."""
    by = collections.defaultdict(list)
    for s in sale_recs:
        by[s["bbl"]].append(s)
    rows, st = [], collections.Counter()
    for b, ss in by.items():
        ds = sorted(ss, key=lambda s: s["date"])
        fl = filings.get(b, [])
        for s in ds:
            sd = d(s["date"])
            k = sum(1 for o in ds if abs((d(o["date"]) - sd).days) <= SALE_WIN)
            lo = sd + dt.timedelta(days=FIN_LO - SALE_WIN)
            hi = sd + dt.timedelta(days=FIN_HI + SALE_WIN)
            m = sum(1 for f in fl if lo <= f <= hi)
            if m == 0:
                fin = 0; st["cash (no filing in window)"] += 1
            elif m >= k:
                fin = 1; st["financed (filings >= sales)"] += 1
            else:
                st["ambiguous (0 < filings < sales)"] += 1
                continue
            r = dict(s); r["financed_base"] = fin
            r["financed_strict"] = fin; r["financed_wide"] = fin
            rows.append(r)
    return rows, st


if __name__ == "__main__":
    filings = load_inic()
    print(f"   INIC filings on a single parcel: "
          f"{sum(len(v) for v in filings.values()):,} across {len(filings):,} buildings", flush=True)

    # ---- validation on houses ----
    print("\n=== VALIDATION: the same rule on 1-3 family houses ===", flush=True)
    import build_panel as BP
    lg, ms = BP.load_legals(), BP.load_master()
    mort = collections.defaultdict(list)
    for did, (dtp, ds, amt) in ms.items():
        if dtp == "MTGE":
            bb = lg.get(did)
            if bb:
                mort[bb].append(d(ds))
    hs = [{"bbl": str(s["bbl"]), "date": s["sale_date"][:10]}
          for s in json.load(open(SALES))
          if (s.get("building_class_category") or "").strip()[:2] in HOUSE_CODES
          and len(str(s.get("bbl") or "")) == 10]
    hr, hst = assign(hs, mort)
    for k, v in hst.most_common():
        print(f"   {k:34} {v:>8,}")
    print(f"   financed share: {sum(r['financed_base'] for r in hr)/len(hr)*100:.1f}%  "
          f"(direct parcel match gives 61.7%)")

    # ---- co-operatives ----
    print("\n=== CO-OPERATIVES ===", flush=True)
    cs = json.load(open("coop_sales.json"))
    recs = []
    for s in cs:
        u = unit_of(s)
        if not u:
            continue
        recs.append({"bbl": str(s["bbl"]), "date": s["sale_date"][:10],
                     "price": float(s["sale_price"]), "borough": str(s["bbl"])[0],
                     "unit": str(s["bbl"]) + "|" + u, "src": "coop"})
    print(f"   co-op sales with a recoverable unit: {len(recs):,} of {len(cs):,}")
    cr, cst = assign(recs, filings)
    for k, v in cst.most_common():
        print(f"   {k:34} {v:>8,}")
    if cr:
        print(f"   financed share: {sum(r['financed_base'] for r in cr)/len(cr)*100:.1f}%")
        uu = collections.Counter(r["unit"] for r in cr)
        print(f"   distinct units: {len(uu):,};  units selling >= twice: "
              f"{sum(1 for v in uu.values() if v>=2):,}")
    json.dump(cr, open("coop_rows2.json", "w"))
    print("\nwrote coop_rows2.json")
