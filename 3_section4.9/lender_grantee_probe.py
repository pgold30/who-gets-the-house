"""Can a lender-as-grantee flag stand in for the foreclosure data ACRIS lacks?

Section 8 says distress is the binding limitation and that foreclosure flags are
not available at usable volume. But a deed whose GRANTEE is a bank or servicer is
an REO/foreclosure transfer, and ACRIS Parties names it. This asks how many pairs
carry one and what the estimator does without them.
"""
import gzip, csv, json, collections, datetime as dt, bisect, os, re
import os
import numpy as np
SP = os.path.dirname(os.path.abspath(__file__))
S12 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2_reproduce")
src = open(SP + "/split_main.py").read()
exec(src.split("# ---------------------------------------------- author's estimator, verbatim")[1]
        .split("# ------------------------------------------------------------------- 1. panel")[0])

rows = [r for r in csv.DictReader(gzip.open(S12 + "/panel2.csv.gz", "rt", newline=""))
        if r["borough"] != "5"]
P36 = build([r for r in rows if r["src"] == "house"], int(36 * 30.44))
deedmap = json.load(open(SP + "/deeds_for_pairs.json"))
gr = json.load(open(SP + "/grantees_main.json"))
for p in P36:
    for s, sd in ((p[0], p[2]), (p[1], p[3])):
        best, bd = None, 46
        for ds, did in deedmap.get(s["bbl"], ()):
            g = abs((dt.date.fromisoformat(ds) - sd).days)
            if g < bd: best, bd = did, g
        s["deed"] = best

# A bare "N.A." token matched 19 Chinese and Korean surnames containing "Na"
# ("CHEN, NA", "NA, JESSICA"). Dropped in favour of the explicit
# "NATIONAL ASSOCIATION", which catches the securitization trustees without
# the surnames.
LENDER = re.compile(r"\b(BANK|MORTGAGE|SERVICING|LOAN|FEDERAL NATIONAL|FANNIE MAE|"
                    r"FREDDIE MAC|SECRETARY OF HOUSING|CERTIFICATEHOLDERS|MERS|"
                    r"SAVINGS|NATIONAL ASSOCIATION)\b", re.I)
def lender(s):
    return any(LENDER.search(x.upper()) for x in gr.get(s.get("deed") or "", []))

flag = np.array([lender(a) or lender(z) for a, z, _, _ in P36])
BORO = {"MANHATTAN":1,"BRONX":2,"BROOKLYN":3,"QUEENS":4,"STATEN ISLAND":5}
perm = collections.defaultdict(list)
with gzip.open(S12 + "/dob_permits.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        b = BORO.get((r["borough"] or "").strip().upper())
        try:
            blk, lot = int(r["block"]), int(r["lot"])
            dd = dt.datetime.strptime(r["issuance_date"].strip(), "%m/%d/%Y").date()
        except Exception: continue
        if b and dd.year >= 2010: perm[f"{b}{blk:05d}{lot:04d}"].append(dd)
for k in perm: perm[k].sort()
def hasp(bbl, da, dz):
    v = perm.get(bbl)
    if not v: return False
    i = bisect.bisect_left(v, da); return i < len(v) and v[i] <= dz
pf = np.array([not hasp(a["bbl"], da, dz) for a, z, da, dz in P36])

k = kinds(P36)
print(f"pairs with a lender/REO grantee on either deed: {int(flag.sum()):,} "
      f"of {len(P36):,} ({flag.mean()*100:.2f}%)")
print(f"  of which cash->fin {int(((k=='cash->fin')&flag).sum()):,}, "
      f"fin->cash {int(((k=='fin->cash')&flag).sum()):,}")
print()
for tag, m in (("permit-free, all", pf),
               ("permit-free, drop lender/REO pairs", pf & ~flag)):
    summ([P36[i] for i in np.where(m)[0]], tag, bs=False)
