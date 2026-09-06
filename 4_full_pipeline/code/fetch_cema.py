"""CEMA detection.

A New York purchase can be financed by a Consolidation, Extension and
Modification Agreement: the buyer takes an assignment of the seller's existing
mortgage and records a new instrument covering only the new money, paying the
mortgage recording tax on that difference alone. ACRIS records these under
doc_type M&CON, "MORTGAGE AND CONSOLIDATION".

Two things follow, and both matter for this paper.

(1) Section 5.2 computes the recording-tax burden from the full loan amount on
    every financed purchase. Where a CEMA was used, the tax was paid on less
    than the full amount, so 1.41% is an upper bound.

(2) The financing flag of Section 3.2 is built from MTGE documents. A purchase
    financed by CEMA records an M&CON and no MTGE, so it would be classified as
    CASH. If CEMA purchases are common the flag is contaminated in the direction
    that matters.

This script measures both.
"""
import urllib.request, urllib.parse, json, time, gzip, csv

M = "https://data.cityofnewyork.us/resource/bnx9-e6tj.csv?"
L = "https://data.cityofnewyork.us/resource/8h5j-fqxa.csv?"


def get(base, params, tries=8):
    u = base + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(u, timeout=180) as r:
                return r.read().decode("utf8", "replace")
        except Exception as e:
            print(f"   retry {i+1} {type(e).__name__}", flush=True)
            time.sleep(3 * (i + 1))
    raise SystemExit("giving up")


rows, off = [], 0
while True:
    t = get(M, {"$select": "document_id,doc_type,document_date,recorded_datetime,document_amt",
                "$where": "doc_type='M&CON' AND recorded_datetime>'2015-06-01'",
                "$order": "document_id", "$limit": 50000, "$offset": off})
    lines = t.splitlines()
    if len(lines) <= 1:
        break
    rows += [l for l in lines[1:]]
    hdr = lines[0]
    off += 50000
    print(f"   master {len(rows):,}", flush=True)
    if len(lines) - 1 < 50000:
        break
with gzip.open("cema_master.csv.gz", "wt", newline="") as fh:
    fh.write(hdr + "\n" + "\n".join(rows) + "\n")

ids = [r.split(",")[0].strip('"') for r in rows]
print(f"{len(ids):,} M&CON documents", flush=True)

out, hdr2, B = [], None, 400
for i in range(0, len(ids), B):
    chunk = ids[i:i + B]
    q = ",".join("'" + c + "'" for c in chunk)
    t = get(L, {"$select": "document_id,borough,block,lot,property_type",
                "$where": f"document_id in({q})", "$limit": 50000})
    lines = t.splitlines()
    hdr2 = lines[0]
    out += lines[1:]
    if (i // B) % 10 == 0:
        print(f"   legals {len(out):,} after {i+len(chunk):,} ids", flush=True)
with gzip.open("cema_legals.csv.gz", "wt", newline="") as fh:
    fh.write(hdr2 + "\n" + "\n".join(out) + "\n")
print(f"done: {len(out):,} legal rows", flush=True)
