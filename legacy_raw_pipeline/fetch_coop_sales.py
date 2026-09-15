"""Co-operative sales with apartment numbers.

The C6 analysis sample kept only price, date, borough, class and parcel. For
co-operatives the parcel is the BUILDING, so a unit identifier needs the
apartment number as well, and it has to be re-fetched.
"""
import urllib.request, urllib.parse, json, time

BASE = "https://data.cityofnewyork.us/resource/w2pb-icbu.json"
CODES = ["09", "10", "17"]
PRICE_MIN, PRICE_MAX = 300_000, 6_000_000


def get(url, tries=8):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.load(r)
        except Exception as e:
            print(f"    retry {i+1}: {str(e)[:55]}", flush=True)
            time.sleep(4 * (i + 1))
    raise SystemExit("giving up")


where = "(" + " OR ".join(f"building_class_category like '{c}%'" for c in CODES) + ")"
rows, off = [], 0
while True:
    q = urllib.parse.urlencode({
        "$select": "sale_price,sale_date,borough,building_class_category,bbl,apartment_number,address",
        "$where": where, "$order": "sale_date, bbl, apartment_number, sale_price",
        "$limit": 50000, "$offset": off})
    b = get(f"{BASE}?{q}")
    rows += b
    off += len(b)
    print(f"   fetched {len(b):,}  total {len(rows):,}", flush=True)
    if len(b) < 50000:
        break
    time.sleep(1)

keep = []
for r in rows:
    try:
        p = float(r.get("sale_price") or 0)
    except ValueError:
        continue
    if PRICE_MIN < p < PRICE_MAX and len(str(r.get("bbl") or "")) == 10:
        keep.append(r)
json.dump(keep, open("coop_sales.json", "w"))
withapt = sum(1 for r in keep if (r.get("apartment_number") or "").strip())
print(f"\nco-op sales in price band: {len(keep):,}")
print(f"  carrying an apartment number: {withapt:,} ({withapt/len(keep)*100:.1f}%)")
