"""Do the 744 unresolved pairs differ from the classified ones?

A pair is unresolved when the deed match failed on one of its two sales, so the
buyer could not be read. If match failure is correlated with anything the
estimator cares about -- price, borough, transition direction, permit incidence,
holding period, or the excess return itself -- the buyer split in
Table 8 is selected rather than random and its levels are biased.

This compares the two groups on all six.
"""
import gzip, csv, json, collections, datetime as dt, bisect, os, re
import os
import numpy as np
from estimator import (q, build, excess, kinds, pisym,
                       boot, summ, rng)

SP = os.path.dirname(os.path.abspath(__file__))
S12 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2_reproduce")
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
            if g < bd:
                best, bd = did, g
        s["deed"] = best

BUSINESS = re.compile(
    r"\b(LLC|L\.?L\.?C|INC|CORP|CORPORATION|COMPANY|LP|L\.?P|LLP|LTD|"
    r"REALTY|PROPERTIES|HOLDINGS?|ASSOCIATES|PARTNERS\w*|VENTURES?|CAPITAL|"
    r"EQUITIES|GROUP|ENTERPRISES?|DEVELOPMENT|BUILDERS?|CONSTRUCTION|"
    r"MANAGEMENT|INVESTMENTS?|FUND|BANK|HOUSING|AUTHORITY)\b", re.I)


def biz(s):
    n = gr.get(s.get("deed") or "", [])
    return None if not n else any(BUSINESS.search(x.upper()) for x in n)


ind = np.array([biz(a) is False and biz(z) is False for a, z, _, _ in P36])
bus = np.array([biz(a) is True or biz(z) is True for a, z, _, _ in P36])
unres = ~(ind | bus)

BORO = {"MANHATTAN": 1, "BRONX": 2, "BROOKLYN": 3, "QUEENS": 4, "STATEN ISLAND": 5}
perm = collections.defaultdict(list)
with gzip.open(S12 + "/dob_permits.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        b = BORO.get((r["borough"] or "").strip().upper())
        try:
            blk, lot = int(r["block"]), int(r["lot"])
            dd = dt.datetime.strptime(r["issuance_date"].strip(), "%m/%d/%Y").date()
        except Exception:
            continue
        if b and dd.year >= 2010:
            perm[f"{b}{blk:05d}{lot:04d}"].append(dd)
for k in perm:
    perm[k].sort()


def hasp(bbl, da, dz):
    v = perm.get(bbl)
    if not v:
        return False
    i = bisect.bisect_left(v, da)
    return i < len(v) and v[i] <= dz


r_all = excess(P36)
k = kinds(P36)
price = np.array([float(a["price"]) for a, z, _, _ in P36])
hold = np.array([(dz - da).days for a, z, da, dz in P36])
pf = np.array([not hasp(a["bbl"], da, dz) for a, z, da, dz in P36])
boro = np.array([a["borough"] for a, z, _, _ in P36])

print("=" * 96)
print("  Do the unresolved pairs differ from the classified ones?")
print("=" * 96)
print(f"  classified {int((~unres).sum()):,}   unresolved {int(unres.sum()):,} "
      f"({unres.mean()*100:.1f}%)\n")


def line(lab, f):
    a, b = f(~unres), f(unres)
    print(f"  {lab:<34} classified {a:>10}   unresolved {b:>10}")


line("median first-sale price", lambda m: f"{np.median(price[m]):,.0f}")
line("median holding (days)", lambda m: f"{np.median(hold[m]):,.0f}")
line("permit-free share", lambda m: f"{pf[m].mean()*100:.1f}%")
line("mean excess return", lambda m: f"{r_all[m].mean():+.4f}")
for kk in ("cash->fin", "fin->cash", "cash->cash", "fin->fin"):
    line(f"share {kk}", lambda m, kk=kk: f"{(k[m]==kk).mean()*100:.1f}%")
for b, nm in (("1", "Manhattan"), ("2", "Bronx"), ("3", "Brooklyn"), ("4", "Queens")):
    line(f"share {nm}", lambda m, b=b: f"{(boro[m]==b).mean()*100:.1f}%")

print("\n  The question that matters: among unresolved pairs, is the estimator")
print("  different? If they are a random subset, pi on them should look like pi")
print("  on the classified ones.")
for lab, m in (("classified pairs", ~unres), ("unresolved pairs", unres)):
    P = [P36[i] for i in np.where(m)[0]]
    v = summ(P, lab, bs=False)
json.dump({"unresolved": int(unres.sum()), "classified": int((~unres).sum())},
          open(SP + "/skew_results.json", "w"))
