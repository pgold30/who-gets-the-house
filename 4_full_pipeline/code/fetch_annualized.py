"""Retrieve NYC DOF annualized calendar sales 2016-2025 (resource w2pb-icbu).

Companion to fetch_nyc_sales.py, which retrieves the rolling twelve-month file.
This one covers 1 Jan 2016 - 31 Dec 2025 and is what makes the pre/post
s.1402-b design possible.

Field-convention warning, verified against the live endpoint on 3 Sep 2026:
calendar year 2016 writes building_class_category with a DOUBLE space after the
two-digit code ("01  ONE FAMILY DWELLINGS"); 2017 onward use a single space.
Filtering on the single-space literals silently drops all of 2016 - the earliest
pre-treatment year - and would manufacture a pre/post difference out of a
formatting change. The filter below matches on the two-digit code only.
"""
import urllib.request, urllib.parse, json, time

BASE = "https://data.cityofnewyork.us/resource/w2pb-icbu.json"
CODES = ["01", "02", "03", "04", "09", "10", "12", "13", "15", "17"]
PRICE_MIN, PRICE_MAX = 300_000, 6_000_000
FIELDS = "sale_price,sale_date,borough,building_class_category,bbl,residential_units,total_units"


def get(url, tries=8):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.load(r)
        except Exception as e:
            print(f"    retry {i+1}: {type(e).__name__} {str(e)[:60]}")
            time.sleep(4 * (i + 1))
    raise SystemExit("giving up on " + url)


def fetch(out="annualized_sales.json"):
    where = " OR ".join(f"building_class_category like '{c}%'" for c in CODES)
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "$select": FIELDS, "$where": f"({where})",
            "$order": "sale_date, bbl, sale_price",
            "$limit": 50000, "$offset": offset})
        batch = get(f"{BASE}?{q}")
        rows += batch
        offset += len(batch)
        print(f"  fetched {len(batch):,}  total {len(rows):,}")
        if len(batch) < 50000:
            break
        time.sleep(1)
    json.dump(rows, open(out, "w"))
    print(f"wrote {len(rows):,} rows -> {out}")
    return rows


if __name__ == "__main__":
    fetch()
