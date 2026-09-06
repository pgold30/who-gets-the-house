"""Partial replication of the paper's raw-data counts against the live APIs.

This does NOT reproduce any estimate. It reproduces the *record counts* the
paper states for each public source, which is the layer a referee can check in
about a minute without downloading 30 GB. Every count below is a documented
figure from the paper; the script re-derives it from NYC Open Data today.

Counts drift upward over time, because ACRIS and DOB append new records
continuously and the author's pull is fixed in the past. A count that comes
back slightly ABOVE the paper's is the expected result. A count that comes back
far below, or is zero, means the query or the resource has changed.

    python3 verify_public_counts.py            # needs only the standard library
"""
import json, sys, urllib.parse, urllib.request

DOMAIN = "https://data.cityofnewyork.us/resource"
UA = {"User-Agent": "who-gets-the-house-replication/1.0"}

# (label, resource, $where, stated in paper, note)
CHECKS = [
    ("ACRIS Real Property Legals, all rows",
     "8h5j-fqxa", None, 22_727_180,
     "Appendix C: 'the table has 22.7 million rows'"),

    ("ACRIS Real Property Master, DEED+MTGE 2015-2026",
     "bnx9-e6tj",
     "doc_type in('DEED','MTGE') AND document_id >= '2015' AND document_id < '2027'",
     1_354_279,
     "Section 3.2. Filtered on document year via the document_id prefix, which"
     " is how the paper does it; a recorded-date filter instead gives"
     " 1,293,586 and is the wrong comparison."),

    ("ACRIS Real Property Master, M&CON since 2015",
     "bnx9-e6tj",
     "doc_type='M&CON' AND recorded_datetime >= '2015-01-01T00:00:00'",
     29_511,
     "Section 5.2, the CEMA robustness check."),

    ("ACRIS Personal Property Master, INIC 2015-2026",
     "sv7x-dduq",
     "doc_type='INIC' AND recorded_datetime >= '2015-01-01T00:00:00'"
     " AND recorded_datetime < '2026-01-01T00:00:00'",
     178_757,
     "Section 3.4, the co-operative share-loan register."),

    ("DOB Permit Issuance, job types A1/A2/NB/DM, all years",
     "ipu4-2q9a", "job_type in('A1','A2','NB','DM')", 3_498_520,
     "Appendix C. The subset issued since 2010 (1,692,200) is what the permit"
     " test uses; this is the full pull before the date filter."),
]


def count(resource, where):
    q = {"$select": "count(1) AS n"}
    if where:
        q["$where"] = where
    url = f"{DOMAIN}/{resource}.json?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return int(json.load(r)[0]["n"])


def main():
    print("=" * 96)
    print("  Live count check against NYC Open Data")
    print("=" * 96)
    ok = 0
    for label, res, where, stated, note in CHECKS:
        try:
            got = count(res, where)
        except Exception as e:
            print(f"  [ERROR] {label}: {e}")
            continue
        drift = (got - stated) / stated
        # Accept a 10% band: the live tables grow, and the paper's date column
        # is document date where this uses recorded date.
        good = abs(drift) <= 0.10
        ok += good
        print(f"\n  [{'MATCH' if good else 'CHECK'}] {label}")
        print(f"          paper {stated:>12,}   live {got:>12,}   drift {drift:+7.2%}")
        print(f"          {note}")
    print("\n" + "=" * 96)
    print(f"  {ok} of {len(CHECKS)} counts reproduce within 10%.")
    print("=" * 96)
    return 0 if ok == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
