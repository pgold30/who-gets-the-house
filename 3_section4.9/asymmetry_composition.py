"""Why do the two corrections disagree? Decompose the arms.

pi_sym = (rbar_cf - rbar_fc)/2 and A = rbar_cf + rbar_fc, so both are functions
of two arm means. If REO transfers enter the two arms at DIFFERENT rates, they
shift rbar_cf and rbar_fc by different amounts, which moves A even if every
pair's condition change were zero. Appendix B reads A entirely as condition
change. Composition imbalance is a third source it does not model.
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
# A bare "N.A." token matched 19 Chinese and Korean surnames containing "Na"
# ("CHEN, NA", "NA, JESSICA"). Dropped in favour of the explicit
# "NATIONAL ASSOCIATION", which catches the securitization trustees without
# the surnames.
LENDER = re.compile(r"\b(BANK|MORTGAGE|SERVICING|LOAN|FEDERAL NATIONAL|FANNIE MAE|"
                    r"FREDDIE MAC|SECRETARY OF HOUSING|CERTIFICATEHOLDERS|MERS|"
                    r"SAVINGS|NATIONAL ASSOCIATION)\b", re.I)
def lend(s): return any(LENDER.search(x.upper()) for x in gr.get(s.get("deed") or "", []))
reo = np.array([lend(a) or lend(z) for a, z, _, _ in P36])

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

# restrict to permit-free, then decompose the two arms
idx = np.where(pf)[0]
P = [P36[i] for i in idx]; R = reo[idx]
r = excess(P); k = kinds(P)

def arm(mask, kk): return r[(k == kk) & mask]

print("=" * 92)
print("  PERMIT-FREE PAIRS: how REO transfers enter each arm")
print("=" * 92)
ALL = np.ones(len(P), bool)
for lab, m in (("all", ALL), ("REO", R), ("non-REO", ~R)):
    a_, b_ = arm(m, "cash->fin"), arm(m, "fin->cash")
    pi = (a_.mean() - b_.mean()) / 2 if len(a_) and len(b_) else float("nan")
    A = a_.mean() + b_.mean() if len(a_) and len(b_) else float("nan")
    print(f"  {lab:<9} n_cf {len(a_):>5,}  rbar_cf {a_.mean():+.4f}   "
          f"n_fc {len(b_):>4,}  rbar_fc {b_.mean():+.4f}   pi {pi:+.4f}  A {A:+.4f}")

ncf_r, ncf_n = len(arm(R, "cash->fin")), len(arm(~R, "cash->fin"))
nfc_r, nfc_n = len(arm(R, "fin->cash")), len(arm(~R, "fin->cash"))
print(f"\n  REO share of the cash->financed arm : {ncf_r/(ncf_r+ncf_n)*100:5.1f}%")
print(f"  REO share of the financed->cash arm : {nfc_r/(nfc_r+nfc_n)*100:5.1f}%")
print(f"  imbalance ratio                     : {(ncf_r/(ncf_r+ncf_n))/(nfc_r/(nfc_r+nfc_n)):5.2f}x")

print("\n" + "=" * 92)
print("  Does composition imbalance alone generate the asymmetry?")
print("=" * 92)
# Reweight the cash->fin arm so REO enters it at the SAME rate as in fin->cash.
p_target = nfc_r / (nfc_r + nfc_n)
cf_r, cf_n = arm(R, "cash->fin"), arm(~R, "cash->fin")
fc_all = arm(ALL, "fin->cash")
rbar_cf_bal = p_target * cf_r.mean() + (1 - p_target) * cf_n.mean()
pi_bal = (rbar_cf_bal - fc_all.mean()) / 2
A_bal = rbar_cf_bal + fc_all.mean()
print(f"  observed          rbar_cf {arm(ALL,'cash->fin').mean():+.4f}  "
      f"pi {(arm(ALL,'cash->fin').mean()-fc_all.mean())/2:+.4f}  A {arm(ALL,'cash->fin').mean()+fc_all.mean():+.4f}")
print(f"  arms balanced     rbar_cf {rbar_cf_bal:+.4f}  pi {pi_bal:+.4f}  A {A_bal:+.4f}")
print(f"\n  Balancing the arms on REO share alone moves A from "
      f"{arm(ALL,'cash->fin').mean()+fc_all.mean():+.4f} to {A_bal:+.4f}, i.e. "
      f"{(A_bal-(arm(ALL,'cash->fin').mean()+fc_all.mean()))/abs(arm(ALL,'cash->fin').mean()+fc_all.mean())*100:.0f}% "
      f"of the way to zero,")
print("  with no appeal to condition change at all.")
print(f"\n  corrected, balanced: pi = {pi_bal:+.4f} + {A_bal:+.4f}/2 = {pi_bal + A_bal/2:+.4f}")
