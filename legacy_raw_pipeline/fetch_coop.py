"""Retrieve co-operative share loans from ACRIS Personal Property.

Section 2.3 explains why co-operative purchases are invisible in the real-property
records: a share loan is a security interest in personalty, perfected by UCC
filing, not a mortgage. It is not, however, invisible in ACRIS. It is filed in the
PERSONAL property records, as document type INIC - "INITIAL COOP UCC1".

  sv7x-dduq  Personal Property Master  - doc_type, recording date
  uqqa-hym2  Personal Property Legals  - borough / block / lot

The limitation that remains: the legals record identifies the BUILDING (the
co-operative corporation's parcel), not the apartment, because the debtor's
collateral is shares rather than a lot. Unit-level assignment therefore depends
on a uniqueness rule, applied and validated in coop_match.py.
"""
import urllib.request, urllib.parse, time, gzip

def get(res, params, tries=8):
    u = f"https://data.cityofnewyork.us/resource/{res}.csv?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(u, timeout=240) as r:
                return r.read().decode("utf8", "replace")
        except Exception as e:
            print(f"      retry {i+1}: {type(e).__name__} {str(e)[:55]}", flush=True)
            time.sleep(4 * (i + 1))
    raise SystemExit("giving up")


def cursor_page(res, select, where_tpl, out, key="document_id", lo="2015", hi="2027", limit=50000):
    cur, n, first = lo, 0, True
    with gzip.open(out, "wt", newline="") as fh:
        while True:
            txt = get(res, {"$select": select,
                            "$where": where_tpl.format(cur=cur, hi=hi),
                            "$order": key, "$limit": limit})
            lines = txt.splitlines()
            got = len(lines) - 1
            if got <= 0:
                break
            fh.write("\n".join(lines if first else lines[1:]) + "\n")
            first = False
            n += got
            cur = lines[-1].split(",")[0].strip('"')
            print(f"      +{got:,}  total {n:,}  cursor {cur}", flush=True)
            if got < limit:
                break
    return n


print("PP MASTER: INIC (co-op UCC1) 2015-2026", flush=True)
n1 = cursor_page("sv7x-dduq", "document_id,doc_type,recorded_datetime,document_amt",
                 "document_id > '{cur}' AND document_id < '{hi}' AND doc_type='INIC'",
                 "pp_master_inic.csv.gz")
print(f"MASTER done: {n1:,}\n", flush=True)

print("PP LEGALS 2015-2026", flush=True)
n2 = cursor_page("uqqa-hym2", "document_id,borough,block,lot,property_type",
                 "document_id > '{cur}' AND document_id < '{hi}'",
                 "pp_legals.csv.gz")
print(f"LEGALS done: {n2:,}", flush=True)
