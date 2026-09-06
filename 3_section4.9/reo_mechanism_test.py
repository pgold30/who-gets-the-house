"""Test the claimed mechanism in the data, not the statute.

Claim: a deed-in-lieu records the satisfied DEBT, not market value, so the
bank's taking-title price is inflated on an underwater loan; the later REO
liquidation is at market. If true, REO pairs should show the first sale
NOMINALLY ABOVE the second far more often than ordinary pairs do -- and over a
2016-2025 window of rising prices, that is a strong signal, because ordinary
repeat pairs almost never fall in nominal terms.
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
            if g < bd: best, bd = did, g
        s["deed"] = best
LENDER = re.compile(r"\b(BANK|MORTGAGE|SERVICING|LOAN|FEDERAL NATIONAL|FANNIE MAE|"
                    r"FREDDIE MAC|SECRETARY OF HOUSING|CERTIFICATEHOLDERS|MERS|"
                    r"SAVINGS|NATIONAL ASSOCIATION)\b", re.I)
def lend(s): return any(LENDER.search(x.upper()) for x in gr.get(s.get("deed") or "", []))

# REO pairs where the LENDER IS THE FIRST BUYER -- the deed-in-lieu leg
first_is_lender = np.array([lend(a) for a, z, _, _ in P36])
second_is_lender = np.array([lend(z) for a, z, _, _ in P36])
p1 = np.array([float(a["price"]) for a, z, _, _ in P36])
p2 = np.array([float(z["price"]) for a, z, _, _ in P36])
k = kinds(P36)
fell = p2 < p1

print("=" * 88)
print("  Nominal price FELL between the two sales, 2016-2025 (a rising market)")
print("=" * 88)
for lab, m in (("all house pairs", np.ones(len(P36), bool)),
               ("lender is the FIRST buyer", first_is_lender),
               ("lender is the SECOND buyer", second_is_lender),
               ("no lender either side", ~(first_is_lender | second_is_lender))):
    if m.sum() == 0: continue
    print(f"  {lab:<32} n {int(m.sum()):>5,}   fell {fell[m].mean()*100:5.1f}%   "
          f"median P1 {np.median(p1[m]):>9,.0f}  median P2 {np.median(p2[m]):>9,.0f}")

print("\n  Direction of the lender-first pairs:")
for kk in ("cash->fin", "fin->cash", "cash->cash", "fin->fin"):
    n = int(((k == kk) & first_is_lender).sum())
    print(f"    {kk:<12} {n:>4,}")
print("\n  The mechanism predicts: lender acquires WITHOUT a new mortgage (cash),")
print("  resells to a financed retail buyer -> cash->fin, and the recorded")
print("  taking-title price exceeds the later market sale.")

# --- roundness: a negotiated market price clusters on round numbers; a
#     satisfied DEBT BALANCE does not. This separates the two hypotheses
#     without any appeal to the statute.
def roundness(v):
    v = np.asarray(v)
    return dict(r10k=float(np.mean(v % 10_000 == 0)),
                r5k=float(np.mean(v % 5_000 == 0)),
                r1k=float(np.mean(v % 1_000 == 0)),
                r100=float(np.mean(v % 100 == 0)))
print("\n" + "=" * 88)
print("  Is the first-sale price a negotiated price or a debt balance?")
print("=" * 88)
print(f"  {'sample':<32}{'n':>7}{'ends 0000':>11}{'mult of 5k':>12}"
      f"{'mult of 1k':>12}{'mult of 100':>13}")
for lab, m in (("lender is the FIRST buyer", first_is_lender),
               ("no lender either side", ~(first_is_lender | second_is_lender))):
    d = roundness(p1[m])
    print(f"  {lab:<32}{int(m.sum()):>7,}{d['r10k']*100:>10.1f}%"
          f"{d['r5k']*100:>11.1f}%{d['r1k']*100:>11.1f}%{d['r100']*100:>12.1f}%")
print("\n  A market price is negotiated to a round number. A debt payoff is not.")
