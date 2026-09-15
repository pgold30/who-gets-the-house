"""DOB alteration permits, for the renovation test.

The symmetry test of Section 4.3 assumes improvement runs cash-then-financed. A
referee's objection: if cash also concentrates in DETERIORATED properties on the
financed-to-cash side, the two condition shocks cancel in the asymmetry statistic
while both remain in the symmetric one. Then A = 0 proves nothing.

The direct answer is to observe renovation rather than infer it. NYC Department
of Buildings permit issuance (ipu4-2q9a) records every alteration permit with
borough, block, lot, job type and issuance date. Job types A1 (alteration with
change of use or occupancy), A2 (alteration, multiple work types), NB (new
building) and DM (demolition) are the substantial ones.

Note on the data: issuance_date is stored as TEXT in MM/DD/YYYY, and dobrundate
is a file-refresh timestamp rather than an event date, so neither supports a
server-side date filter. The full set of A1/A2/NB/DM permits is therefore pulled
and filtered locally.
"""
import urllib.request, urllib.parse, time, gzip

B = "https://data.cityofnewyork.us/resource/ipu4-2q9a.csv?"
LIMIT = 50000


def get(params, tries=8):
    u = B + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(u, timeout=300) as r:
                return r.read().decode("utf8", "replace")
        except Exception as e:
            print(f"      retry {i+1}: {type(e).__name__} {str(e)[:55]}", flush=True)
            time.sleep(4 * (i + 1))
    raise SystemExit("giving up")


cur, n, first = "", 0, True
with gzip.open("dob_permits.csv.gz", "wt", newline="") as fh:
    while True:
        where = "job_type in('A1','A2','NB','DM')"
        if cur:
            where += f" AND job__ > '{cur}'"
        txt = get({"$select": "job__,borough,block,lot,job_type,issuance_date",
                   "$where": where, "$order": "job__", "$limit": LIMIT})
        lines = txt.splitlines()
        got = len(lines) - 1
        if got <= 0:
            break
        fh.write("\n".join(lines if first else lines[1:]) + "\n")
        first = False
        n += got
        cur = lines[-1].split(",")[0].strip('"')
        if n % 250000 < LIMIT:
            print(f"      total {n:,}  cursor {cur}", flush=True)
        if got < LIMIT:
            break
print(f"DOB done: {n:,}", flush=True)
