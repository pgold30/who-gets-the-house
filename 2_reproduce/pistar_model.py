"""pi* from a seller's problem, rather than imported and scaled.

The paper's weakest input was pi*, taken from Reher and Valkanov's national
decomposition and scaled by a denial ratio. This replaces it with a transparent
two-parameter model whose inputs are (a) measurable from HMDA and (b) explicit.

THE MODEL. A seller holds a property worth P. A cash offer C closes with
certainty. A financed offer F closes with probability 1-q. If it fails the seller
re-lists, eventually realising P again but bearing a cost delta - carrying costs,
time on market, and the price penalty a re-listed property suffers. Write
d = delta/P for that cost as a share of price. A risk-neutral seller is
indifferent when

    C = (1-q) F + q (P - delta).

Setting F = C/(1-pi*) at the indifference point and P = C gives

    pi* = q d / (1 - q + q d).                                            (3)

pi* is increasing in both the probability a financed deal fails and the cost of
its failing, and is approximately q*d when both are small.

WHY THIS IS BETTER. It makes the assumption visible. Instead of a number imported
from another market, the reader sees exactly what has to be true for a given pi*.
And it can be INVERTED: given the measured premium, equation (3) says what
re-listing cost would be needed to justify it. If that cost is implausible, the
premium is not compensation for risk, and no appeal to a national estimate is
required to say so.

    d* = pi* (1 - q) / (q (1 - pi*)).                                     (4)
"""
import urllib.request, urllib.parse, json, time
import numpy as np

B = "https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations?"
NYC = ["36005", "36047", "36061", "36081", "36085"]
STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY",
          "LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND",
          "OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"]
YEARS = ["2019", "2020", "2021", "2022", "2023"]


def get(p, tries=6):
    u = B + urllib.parse.urlencode(p)
    for i in range(tries):
        try:
            with urllib.request.urlopen(u, timeout=120) as r:
                return json.load(r)
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def counts(p):
    a = get(p)
    if not a:
        return None
    return {x["actions_taken"]: x["count"] for x in a.get("aggregations", [])}


print("=" * 96)
print("q  THE PROBABILITY A FINANCED PURCHASE FAILS  (HMDA home-purchase applications)")
print("=" * 96)
print("   action codes: 1 originated, 2 approved-not-accepted, 3 denied,")
print("                 4 withdrawn by applicant, 5 file closed for incompleteness")
print()
print(f"{'year':>6} {'denied only':>26} {'denied + incomplete':>22} {'+ withdrawn':>16}")
print(f"{'':>6} {'NYC':>12} {'US':>12} {'NYC':>10} {'US':>10} {'NYC':>7} {'US':>7}")
rows = []
for y in YEARS:
    base = {"years": y, "loan_purposes": "1", "actions_taken": "1,2,3,4,5"}
    n = counts({**base, "counties": ",".join(NYC)})
    u = counts({**base, "states": ",".join(STATES)})
    if not n or not u:
        print(f"{y:>6}   query failed")
        continue
    def rates(d):
        tot = sum(int(d.get(str(k), 0)) for k in range(1, 6))
        den = int(d.get("3", 0)); inc = int(d.get("5", 0)); wd = int(d.get("4", 0))
        return den/tot, (den+inc)/tot, (den+inc+wd)/tot
    rn, ru = rates(n), rates(u)
    rows.append(dict(year=y, nyc=rn, us=ru))
    print(f"{y:>6} {rn[0]*100:11.2f}% {ru[0]*100:11.2f}% {rn[1]*100:9.2f}% {ru[1]*100:9.2f}% "
          f"{rn[2]*100:6.2f}% {ru[2]*100:6.2f}%")

if rows:
    q_narrow = float(np.mean([r["nyc"][0] for r in rows]))
    q_mid = float(np.mean([r["nyc"][1] for r in rows]))
    q_wide = float(np.mean([r["nyc"][2] for r in rows]))
    print(f"\n   NYC means:  denied {q_narrow*100:.2f}%   denied+incomplete {q_mid*100:.2f}%   "
          f"+withdrawn {q_wide*100:.2f}%")
    print("\n   An application in HMDA carries a property address, so these are applications")
    print("   on identified properties rather than pre-approval enquiries. They still")
    print("   OVERSTATE fall-through, because some applications precede an accepted offer.")
    print("   All three are therefore upper bounds on q, and are used as such.")

    def pistar(q, d):
        return q * d / (1 - q + q * d)

    def d_needed(pi, q):
        return pi * (1 - q) / (q * (1 - pi))

    print()
    print("=" * 96)
    print("pi* IMPLIED BY THE MODEL, equation (3)")
    print("=" * 96)
    print(f"{'re-listing cost d':>18}" + "".join(f"{f'q={q*100:.0f}%':>12}"
          for q in [q_narrow, q_mid, q_wide]))
    grid = {}
    for d in [0.02, 0.05, 0.08, 0.10, 0.15, 0.20]:
        line = f"{d*100:17.0f}%"
        for q in [q_narrow, q_mid, q_wide]:
            line += f"{pistar(q, d)*100:11.2f}%"
        grid[d] = [float(pistar(q, d)) for q in (q_narrow, q_mid, q_wide)]
        print(line)

    print()
    print("=" * 96)
    print("INVERTED: what re-listing cost would JUSTIFY the measured premium?  equation (4)")
    print("=" * 96)
    print(f"{'':>26}" + "".join(f"{f'q={q*100:.0f}%':>14}" for q in [q_narrow, q_mid, q_wide]))
    inv = {}
    for lab, pi in [("houses, pi = 0.1114", 0.1114), ("condominiums, pi = 0.0074", 0.0074),
                    ("Queens houses, pi = 0.1495", 0.1495),
                    ("Manhattan condos, pi = 0.0003", 0.0003)]:
        line = f"{lab:>26}"
        vals = []
        for q in [q_narrow, q_mid, q_wide]:
            dd = d_needed(pi, q); vals.append(float(dd))
            line += f"{dd*100:13.1f}%"
        inv[lab] = vals
        print(line)
    print()
    print("   Read the house row: for an 11.1% discount to be fair compensation, a failed")
    print("   sale would have to cost the seller between a third and three quarters of the")
    print("   property's value. No plausible re-listing cost is anywhere near that.")
    print("   Read the condominium row: 2 to 5 per cent, which is an ordinary estimate of")
    print("   carrying costs plus the penalty a re-listed property pays.")

    json.dump({"q_denied": q_narrow, "q_denied_incomplete": q_mid, "q_plus_withdrawn": q_wide,
               "rows": [{"year": r["year"], "nyc": list(r["nyc"]), "us": list(r["us"])} for r in rows],
               "pistar_grid": grid, "d_needed": inv},
              open("pistar_results.json", "w"), indent=1)
    print("\nwrote pistar_results.json")
