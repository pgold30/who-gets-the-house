"""Borough-level pi with parcel-clustered bootstrap confidence intervals.

Section 12.1 argues that a national average cannot settle the question because
the instrument triggers locally and the sign of its efficiency effect can differ
across markets. If that argument is right it should bite WITHIN a city too, and
a point estimate without an interval cannot establish whether it does.
"""
import numpy as np, json, collections, datetime as dt
from estimate_pi import load
from finalize import build_pairs, excess, pi_sym, BREAKEVEN, BORO

rng = np.random.default_rng(20260903)
rows = load()

print(f"{'borough':<16} {'pairs':>7} {'switchers':>10} {'pi':>8} {'95% CI (clustered boot)':>26} {'vs 0.117':>10}")
out = {}
for b, name in BORO.items():
    P = build_pairs(rows, boro=b)
    if len(P) < 400:
        print(f"{name:<16} {len(P):7,}   too few pairs")
        continue
    v = pi_sym(P, excess(P))
    if not v:
        print(f"{name:<16} {len(P):7,}   too few switching parcels")
        continue
    bbls = np.array([a["bbl"] for a, z, da, dz in P])
    uniq = np.unique(bbls)
    idx = {u: np.where(bbls == u)[0] for u in uniq}
    draws = []
    for _ in range(500):
        samp = rng.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idx[u] for u in samp])
        Pb = [P[i] for i in ii]
        try:
            w = pi_sym(Pb, excess(Pb))
            if w: draws.append(w[0])
        except Exception:
            pass
    draws = np.array(draws)
    ci = np.percentile(draws, [2.5, 97.5])
    verdict = ("CLEARS" if ci[0] >= BREAKEVEN else
               "fails" if ci[1] < BREAKEVEN else "ambiguous")
    out[name] = dict(pairs=len(P), switchers=v[1] + v[2], pi=float(v[0]),
                     ci=[float(ci[0]), float(ci[1])], verdict=verdict)
    print(f"{name:<16} {len(P):7,} {v[1]+v[2]:10,} {v[0]:8.4f} "
          f"[{ci[0]:11.4f},{ci[1]:9.4f}] {verdict:>10}")

print()
print("   CLEARS    = whole 95% interval at or above the 11.7% break-even")
print("   fails     = whole interval below it")
print("   ambiguous = interval straddles it; the data cannot say")
print()
print("   Manhattan is absent because it is overwhelmingly co-operative and")
print("   condominium stock, and neither can be matched to ACRIS mortgages. The")
print("   borough where institutional purchasing is most intense is the one this")
print("   design cannot see - a limitation to state plainly, not to bury.")

json.dump(out, open("boro_results.json", "w"), indent=1)
print("\nwrote boro_results.json")
