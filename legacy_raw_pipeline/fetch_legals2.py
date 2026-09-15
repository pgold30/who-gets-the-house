"""Legals fetch, cursor-paged.

The legals table has no date column, but document_id begins with the recording
year, so a lexicographic range on document_id selects a period. Paging with
`document_id > last_seen` rather than $offset matters: offset paging on a
22.7M-row table degrades badly, and starts_with() is not indexed.
"""
import urllib.request, urllib.parse, time, gzip

B = "https://data.cityofnewyork.us/resource/8h5j-fqxa.csv?"
LO, HI, LIMIT = "2015", "2027", 50000


def get(params, tries=8):
    url = B + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=240) as r:
                return r.read().decode("utf8", "replace")
        except Exception as e:
            print(f"      retry {i+1}: {type(e).__name__} {str(e)[:55]}", flush=True)
            time.sleep(4 * (i + 1))
    raise SystemExit("giving up")


cursor, n, first = LO, 0, True
with gzip.open("acris_legals.csv.gz", "wt", newline="") as fh:
    while True:
        txt = get({"$select": "document_id,borough,block,lot,property_type",
                   "$where": f"document_id > '{cursor}' AND document_id < '{HI}'",
                   "$order": "document_id", "$limit": LIMIT})
        lines = txt.splitlines()
        got = len(lines) - 1
        if got <= 0:
            break
        fh.write("\n".join(lines if first else lines[1:]) + "\n")
        first = False
        n += got
        cursor = lines[-1].split(",")[0].strip('"')
        print(f"      +{got:,}  total {n:,}   cursor {cursor}", flush=True)
        if got < LIMIT:
            break
print(f"LEGALS done: {n:,}", flush=True)
