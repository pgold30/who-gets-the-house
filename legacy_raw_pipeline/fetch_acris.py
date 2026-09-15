"""Retrieve ACRIS master and legals records needed for the Section 12 break-even test.

ACRIS is New York City's public land-records system. Section 12.2 of the paper
says the deed files carrying the concurrent-mortgage indicator are commercially
available; for New York City they are not necessary, because ACRIS is public.

  bnx9-e6tj  Real Property Master  - document type, amount, document and recording dates
  8h5j-fqxa  Real Property Legals  - borough / block / lot for each document

document_id begins with the four-digit recording year, which is what makes the
legals table pageable by period (it carries no date column of its own).
"""
import urllib.request, urllib.parse, json, time, sys, csv, gzip

B = "https://data.cityofnewyork.us/resource/"
YEARS = range(2015, 2027)          # sales run 2016-2025; +/-1 year of margin for recording lag


def get(res, params, tries=8):
    url = f"{B}{res}.csv?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return r.read().decode("utf8", "replace")
        except Exception as e:
            print(f"      retry {i+1}: {type(e).__name__} {str(e)[:60]}", flush=True)
            time.sleep(4 * (i + 1))
    raise SystemExit("giving up: " + url[:120])


def page(res, select, where, order, out, limit=50000):
    """Page a resource to a gzipped CSV, writing the header once."""
    n, offset, first = 0, 0, True
    with gzip.open(out, "wt", newline="") as fh:
        while True:
            txt = get(res, {"$select": select, "$where": where,
                            "$order": order, "$limit": limit, "$offset": offset})
            lines = txt.splitlines()
            if not lines:
                break
            body = lines if first else lines[1:]
            got = len(lines) - 1
            fh.write("\n".join(body) + "\n")
            first = False
            n += got
            offset += got
            print(f"      +{got:,}  total {n:,}", flush=True)
            if got < limit:
                break
            time.sleep(0.5)
    return n


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "both"

    if what in ("master", "both"):
        print("MASTER: deeds and mortgages recorded 2015-2026", flush=True)
        n = page("bnx9-e6tj",
                 "document_id,doc_type,document_date,recorded_datetime,document_amt",
                 "(doc_type='MTGE' OR doc_type='DEED') AND "
                 "recorded_datetime>='2015-01-01T00:00:00' AND "
                 "recorded_datetime<'2027-01-01T00:00:00'",
                 "document_id", "acris_master.csv.gz")
        print(f"MASTER done: {n:,}\n", flush=True)

    if what in ("legals", "both"):
        print("LEGALS: borough/block/lot per document, 2015-2026", flush=True)
        tot = 0
        for y in YEARS:
            print(f"   year {y}", flush=True)
            tot += page("8h5j-fqxa", "document_id,borough,block,lot,property_type",
                        f"starts_with(document_id,'{y}')", "document_id",
                        f"acris_legals_{y}.csv.gz")
        print(f"LEGALS done: {tot:,}", flush=True)
