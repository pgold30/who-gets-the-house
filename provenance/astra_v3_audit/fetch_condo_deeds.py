"""Recover ACRIS deed IDs for archived condominium repeat-sale endpoints.

Every legal and master partition is checked against a separate Socrata count(1).
Condo sales are linked by exact unit parcel plus date and consideration.
"""
import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "FINANCING_V3_0" / "replication"
CACHE = HERE / "condo_pages"


def request(resource, params):
    url = f"https://data.cityofnewyork.us/resource/{resource}.json?" + urllib.parse.urlencode(params)
    for attempt in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "WhoGetsTheHouse-independent-audit/1.0"}), timeout=120) as response:
                return json.load(response)
        except Exception:
            if attempt == 6:
                raise
            time.sleep(min(30, 2 ** attempt))


def checked_page(kind, index, ids):
    dest = CACHE / f"{kind}_{index:04d}.json"
    if dest.exists():
        saved = json.loads(dest.read_text())
        assert saved["keys"] == ids and saved["count"] == len(saved["rows"])
        return saved
    if kind == "legal":
        borough = ids[0][0]
        blocks = sorted({str(int(x[1:6])) for x in ids})
        lots = sorted({str(int(x[6:])) for x in ids})
        where = "borough='" + borough + "' AND block in(" + ",".join("'" + x + "'" for x in blocks) + ") AND lot in(" + ",".join("'" + x + "'" for x in lots) + ") AND document_id >= '2016' AND document_id < '2026'"
        resource, select = "8h5j-fqxa", "document_id,borough,block,lot,property_type"
    else:
        where = "document_id in(" + ",".join("'" + x + "'" for x in ids) + ") AND doc_type='DEED'"
        resource, select = "bnx9-e6tj", "document_id,doc_type,document_date,recorded_datetime,document_amt"
    count = int(request(resource, {"$select": "count(1)", "$where": where})[0]["count_1"])
    assert count < 50000, (kind, index, count)
    rows = request(resource, {"$select": select, "$where": where, "$order": "document_id", "$limit": 50000})
    assert len(rows) == count, (kind, index, len(rows), count)
    saved = {"keys": ids, "count": count, "rows": rows}
    dest.write_text(json.dumps(saved))
    return saved


def parallel(kind, pages):
    gathered = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(checked_page, kind, i, batch): i for i, batch in enumerate(pages)}
        for future in as_completed(futures):
            item = future.result()
            gathered.append((futures[future], item))
            if len(gathered) % 20 == 0:
                print(f"{kind}: verified {len(gathered)}/{len(pages)} pages", flush=True)
    gathered.sort()
    return [row for _, item in gathered for row in item["rows"]]


def main():
    CACHE.mkdir(exist_ok=True)
    panel = pd.read_csv(SRC / "inputs/2_reproduce/panel2.csv.gz", dtype={"bbl": str, "borough": str})
    panel = panel.loc[panel.src.eq("condo") & panel.borough.ne("5")].sort_values(["bbl", "date"], kind="mergesort")
    earlier = panel.groupby("bbl", sort=False).shift(1)
    take = (pd.to_datetime(panel.date) - pd.to_datetime(earlier.date)).dt.days.ge(int(36 * 30.44))
    z, a = panel.loc[take].reset_index(drop=True), earlier.loc[take].reset_index(drop=True)
    pairs = pd.DataFrame({"bbl": z.bbl, "borough": z.borough,
                          "date_a": a.date, "date_z": z.date, "price_a": a.price, "price_z": z.price,
                          "financed_base_a": a.financed_base, "financed_base_z": z.financed_base,
                          "y": np.log(z.price.to_numpy(float) / a.price.to_numpy(float))})
    assert len(pairs) == 6584, len(pairs)
    _, pairs["cluster"] = np.unique(pairs.bbl, return_inverse=True)
    parcels = set(pairs.bbl)
    grouped = defaultdict(list)
    for bbl in sorted(parcels):
        grouped[bbl[0]].append(bbl)
    legal_pages = []
    for borough, values in sorted(grouped.items()):
        byblock = defaultdict(list)
        for bbl in values:
            byblock[bbl[:6]].append(bbl)
        blocks = sorted(byblock)
        for i in range(0, len(blocks), 10):
            legal_pages.append([bbl for block in blocks[i:i+10] for bbl in byblock[block]])
    legals = parallel("legal", legal_pages)
    legal_doc_to_bbl = defaultdict(set)
    for r in legals:
        bbl = str(int(r["borough"])) + str(int(r["block"])).zfill(5) + str(int(r["lot"])).zfill(4)
        if bbl in parcels:
            legal_doc_to_bbl[r["document_id"]].add(bbl)
    docids = sorted(legal_doc_to_bbl)
    master_pages = [docids[i:i+300] for i in range(0, len(docids), 300)]
    deeds = parallel("master", master_pages)
    by_bbl = defaultdict(list)
    for r in deeds:
        did = r["document_id"]
        if len(legal_doc_to_bbl[did]) != 1:
            continue
        day = (r.get("document_date") or r.get("recorded_datetime") or "")[:10]
        try:
            amt = float(r.get("document_amt") or 0)
        except ValueError:
            continue
        if len(day) == 10 and amt > 0:
            by_bbl[next(iter(legal_doc_to_bbl[did]))].append((did, day, amt))
    matched, ambiguous = 0, 0
    for side in ("a", "z"):
        output = []
        for row in pairs.itertuples(index=False):
            date = pd.Timestamp(getattr(row, "date_" + side))
            price = float(getattr(row, "price_" + side))
            candidates = {did for did, day, amt in by_bbl.get(row.bbl, []) if abs((pd.Timestamp(day) - date).days) <= 45 and abs(amt - price) <= .005 * price}
            if len(candidates) == 1:
                output.append(next(iter(candidates))); matched += 1
            else:
                output.append("")
                ambiguous += len(candidates) > 1
        pairs["deed_" + side] = output
    pairs.to_csv(HERE / "condo_pairs_with_deeds.csv", index=False)
    (HERE / "condo_fetch_manifest.json").write_text(json.dumps({
        "source": "NYC ACRIS real-property legals 8h5j-fqxa and master bnx9-e6tj", "legal_pages": len(legal_pages), "legal_rows": len(legals),
        "master_pages": len(master_pages), "master_deeds": len(deeds), "pairs": len(pairs), "unique_parcels": len(parcels),
        "endpoint_deeds_matched": matched, "total_endpoints": 2 * len(pairs), "ambiguous_endpoints": ambiguous,
        "method": "Unit BBL; unique DEED within 45 days and 0.5 percent consideration; every indexed partition verified against count(1)",
    }, indent=2) + "\n")
    print(f"Condo endpoints matched {matched}/{2*len(pairs)}; ambiguous {ambiguous}", flush=True)


if __name__ == "__main__":
    main()
