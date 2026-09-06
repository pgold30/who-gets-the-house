"""Retrieve the New York City residential sales used in Section 10.

Downloads the NYC Department of Finance annualized rolling-sales file from NYC
Open Data (resource usep-8jbt), applies the building-class filter that defines
residential real property for the purposes of NY Tax Law s.1402-a, and writes
nyc_sales.json.

The endpoint is public and needs no key. Re-running reproduces the analysis
sample for the twelve months the paper reports, subject to NYC DOF's rolling
window: the file covers the most recent twelve months, so a later run returns a
later window. The exact extract analysed in the paper (1 August 2025 to 31 July
2026, 39,021 rows) is deposited alongside this script as nyc_sales.json.
"""
import urllib.request, urllib.parse, json, time

BASE = "https://data.cityofnewyork.us/resource/usep-8jbt.json"

# Residential real property under s.1402-a: 1-3 family dwellings, condominium
# units, cooperative apartments. Rental buildings of 4+ units are excluded.
CATEGORIES = [
    "01 ONE FAMILY DWELLINGS", "02 TWO FAMILY DWELLINGS", "03 THREE FAMILY DWELLINGS",
    "04 TAX CLASS 1 CONDOS", "09 COOPS - WALKUP APARTMENTS", "10 COOPS - ELEVATOR APARTMENTS",
    "12 CONDOS - WALKUP APARTMENTS", "13 CONDOS - ELEVATOR APARTMENTS",
    "15 CONDOS - 2-10 UNIT RESIDENTIAL", "17 CONDO COOPS",
]
PRICE_MIN, PRICE_MAX = 300_000, 6_000_000


def fetch(out="nyc_sales.json"):
    cats = ",".join("'" + c.replace("'", "''") + "'" for c in CATEGORIES)
    where = (f"building_class_category in({cats}) "
             f"AND sale_price > {PRICE_MIN} AND sale_price < {PRICE_MAX}")
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "$where": where,
            "$select": "sale_price,sale_date,borough,building_class_category,"
                       "residential_units,total_units",
            "$limit": 50000, "$offset": offset})
        with urllib.request.urlopen(f"{BASE}?{q}", timeout=120) as r:
            batch = json.load(r)
        rows += batch
        offset += len(batch)
        print(f"fetched {len(batch)}, total {len(rows)}")
        if len(batch) < 50000:
            break
        time.sleep(1)
    json.dump(rows, open(out, "w"))
    print(f"wrote {len(rows)} rows to {out}")
    return rows


if __name__ == "__main__":
    fetch()
