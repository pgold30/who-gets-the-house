"""Fetch public ACRIS party addresses for the house sample, with exact count checks.

Requests are partitioned by sorted, indexed document_id values. Every partition
is compared to a separate count(1) query before being accepted.
"""
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "FINANCING_V3_0" / "replication"
CACHE = HERE / "address_pages"
API = "https://data.cityofnewyork.us/resource/636b-3b5g.json"


def request(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "WhoGetsTheHouse-independent-audit/1.0"}), timeout=90) as response:
                return json.load(response)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def page(index, ids):
    dest = CACHE / f"page_{index:04d}.json"
    if dest.exists():
        saved = json.loads(dest.read_text())
        assert saved["document_ids"] == ids
        assert saved["expected"] == len(saved["rows"])
        return saved
    where = "document_id in(" + ",".join("'" + x + "'" for x in ids) + ") AND party_type in('1','2')"
    expected = int(request({"$select": "count(1)", "$where": where})[0]["count_1"])
    rows = request({"$select": "document_id,party_type,name,address_1,address_2,city,zip", "$where": where, "$order": "document_id", "$limit": 50000})
    assert len(rows) == expected, (index, len(rows), expected)
    saved = {"document_ids": ids, "expected": expected, "rows": rows}
    dest.write_text(json.dumps(saved))
    return saved


def main():
    frame = pd.read_csv(SRC / "data/house_pairs_enriched.csv.gz", dtype={"deed_a": str, "deed_z": str})
    frame = frame.loc[frame.permit_free & ~frame.lender_high & frame.geo_linked]
    ids = sorted(set(frame.deed_a.dropna()) | set(frame.deed_z.dropna()))
    CACHE.mkdir(exist_ok=True)
    pages = [ids[i:i + 100] for i in range(0, len(ids), 100)]
    collected = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(page, i, batch): i for i, batch in enumerate(pages)}
        for future in as_completed(futures):
            result = future.result()
            collected.append((futures[future], result))
            if len(collected) % 10 == 0:
                print(f"verified {len(collected)}/{len(pages)} indexed pages", flush=True)
    collected.sort()
    rows = [item for _, page_data in collected for item in page_data["rows"]]
    assert len(rows) == sum(page_data["expected"] for _, page_data in collected)
    (HERE / "house_party_addresses.json").write_text(json.dumps(rows))
    (HERE / "address_fetch_manifest.json").write_text(json.dumps({
        "resource": "636b-3b5g", "indexed_key": "document_id", "requested_document_ids": len(ids),
        "pages": len(pages), "page_document_ids": 100, "rows": len(rows),
        "method": "IN lists over sorted document_id values; per-page count(1) equality required",
    }, indent=2) + "\n")
    print(f"all {len(rows)} rows agree with per-page count(1)", flush=True)


if __name__ == "__main__":
    main()
