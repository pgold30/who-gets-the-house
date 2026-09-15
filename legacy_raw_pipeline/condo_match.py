"""Recover condominium sales by matching each DOF sale to its own ACRIS deed.

The obstacle: DOF bills a condominium unit under a billing lot (7501+) while
ACRIS records instruments against the unit lot (1001-1999). PLUTO does not
bridge them - it carries 11,253 billing lots and only 2,188 unit lots, and
`condono` numbers a condominium within a borough rather than linking its units.

The route that does work: the DEED for a given sale is itself in ACRIS, carrying
the consideration and the date, and its legal record carries the unit lot. So a
DOF sale can be matched to its own deed on borough + block + amount + date, and
that match reveals the unit lot. The financing question is then asked at the
correct parcel.

A match is accepted only when it is UNIQUE. Where several deeds on the same block
share an amount and date the sale is dropped rather than guessed - in a large
condominium that ambiguity is common and a wrong lot would produce a wrong
financing flag.

The method is validated on 1-3 family dwellings, where the DOF and ACRIS parcel
identifiers already agree, so the recovered lot can be checked against the truth.
"""
import json, gzip, csv, collections, datetime as dt

MASTER, LEGALS = "acris_master.csv.gz", "acris_legals.csv.gz"
SALES = "/home/claude/empirical_c6/sample_2016_2025.json"
CONDO_CODES = {"04", "12", "13", "15"}      # tax-class-1 condos, walkup, elevator, 2-10 unit
HOUSE_CODES = {"01", "02", "03"}
AMT_TOL, DAY_TOL = 0.005, 45                # 0.5% on consideration, 45 days on date


def d(s):
    return dt.date.fromisoformat(s[:10])


def load_legals():
    m, multi = {}, set()
    with gzip.open(LEGALS, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                b, bl, lo = int(r["borough"]), int(r["block"]), int(r["lot"])
            except (ValueError, TypeError):
                continue
            did = r["document_id"]
            key = (b, bl, lo)
            if did in m and m[did] != key:
                multi.add(did)
            else:
                m[did] = key
    for x in multi:
        m.pop(x, None)
    print(f"   legals: {len(m):,} single-parcel documents ({len(multi):,} multi dropped)", flush=True)
    return m


def load_master():
    deeds, morts = [], []
    with gzip.open(MASTER, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            ds = (r.get("document_date") or r.get("recorded_datetime") or "")[:10]
            if len(ds) < 10:
                continue
            try:
                amt = float(r.get("document_amt") or 0)
            except ValueError:
                continue
            # Only plain DEED and MTGE. An earlier version routed every non-DEED
            # type into the mortgage list, so satisfactions, assignments and
            # agreements recorded near a sale marked it financed. That inflates
            # the financed share and biases pi towards zero.
            if r["doc_type"] == "DEED":
                deeds.append((r["document_id"], ds, amt))
            elif r["doc_type"] == "MTGE":
                morts.append((r["document_id"], ds, amt))
    print(f"   master: {len(deeds):,} deeds, {len(morts):,} mortgages", flush=True)
    return deeds, morts


def index_deeds(deeds, legals, lot_lo, lot_hi):
    """deeds keyed by (borough, block) -> list of (date, amount, lot)"""
    ix = collections.defaultdict(list)
    for did, ds, amt in deeds:
        k = legals.get(did)
        if not k or amt <= 0:
            continue
        b, bl, lo = k
        if lot_lo <= lo <= lot_hi:
            ix[(b, bl)].append((d(ds), amt, lo))
    return ix


def match(sales, ix, codes):
    """Return (matched, stats). A sale matches when exactly one deed on its block
    agrees on amount and date."""
    matched, st = [], collections.Counter()
    for s in sales:
        cat = (s.get("building_class_category") or "").strip()[:2]
        if cat not in codes:
            continue
        b = str(s.get("bbl") or "")
        if len(b) != 10:
            st["no bbl"] += 1
            continue
        boro, blk = int(b[0]), int(b[1:6])
        price, sd = float(s["sale_price"]), d(s["sale_date"])
        cands = [(lo, ds, amt) for ds, amt, lo in ix.get((boro, blk), [])
                 if abs(amt - price) <= AMT_TOL * price and abs((ds - sd).days) <= DAY_TOL]
        lots = {lo for lo, _, _ in cands}
        if not lots:
            st["no deed found"] += 1
        elif len(lots) > 1:
            st["ambiguous (several lots)"] += 1
        else:
            st["matched"] += 1
            matched.append((s, f"{boro}{blk:05d}{list(lots)[0]:04d}"))
    return matched, st


if __name__ == "__main__":
    legals = load_legals()
    deeds, morts = load_master()
    sales = json.load(open(SALES))

    print("\n=== VALIDATION on 1-3 family, where the true lot is known ===", flush=True)
    ixh = index_deeds(deeds, legals, 1, 7499)
    mh, sh = match(sales, ixh, HOUSE_CODES)
    ok = sum(1 for s, bbl in mh if bbl == str(s["bbl"]))
    for k, v in sh.most_common():
        print(f"   {k:28} {v:>8,}")
    if mh:
        print(f"   recovered lot equals the true lot: {ok:,}/{len(mh):,} = {ok/len(mh)*100:.1f}%")

    print("\n=== CONDOMINIUMS ===", flush=True)
    ixc = index_deeds(deeds, legals, 1001, 1999)
    mc, sc = match(sales, ixc, CONDO_CODES)
    for k, v in sc.most_common():
        print(f"   {k:28} {v:>8,}")
    tot = sum(sc.values())
    if tot:
        print(f"   match rate: {sc['matched']/tot*100:.1f}% of condo sales")

    # financing flag at the recovered unit lot
    mort_by = collections.defaultdict(list)
    for did, ds, amt in morts:
        k = legals.get(did)
        if k:
            mort_by[f"{k[0]}{k[1]:05d}{k[2]:04d}"].append(d(ds))
    rows = []
    for s, bbl in mc:
        sd = d(s["sale_date"])
        ms = mort_by.get(bbl, [])
        rec = {"bbl": bbl, "date": sd.isoformat(), "price": float(s["sale_price"]),
               "borough": bbl[0], "src": "condo"}
        for name, (lo, hi) in {"strict": (-15, 30), "base": (-15, 90), "wide": (-15, 180)}.items():
            a, z = sd + dt.timedelta(days=lo), sd + dt.timedelta(days=hi)
            rec[f"financed_{name}"] = int(any(a <= m <= z for m in ms))
        rows.append(rec)
    if rows:
        fin = sum(r["financed_base"] for r in rows) / len(rows)
        print(f"\n   condo sales with a financing flag: {len(rows):,}")
        print(f"   financed share: {fin*100:.1f}%   (1-3 family was 61.7%)")
    json.dump(rows, open("condo_rows.json", "w"))
    print("\nwrote condo_rows.json")
