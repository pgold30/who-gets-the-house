"""Local denial rates for pi*, the actuarially justified part of the premium.

Section 12.4 requires an estimate of pi*_m alongside equation (7), because (7)
identifies the gross premium only. Reher and Valkanov put pi* at 3.3% for a
representative seller and 6.9% once heterogeneity in local denial rates is
allowed for. Neither is a New York number.

HMDA gives application outcomes by county, so the ratio of the New York City
denial rate to the national one scales those national figures to this market.

IMPORTANT LIMITATION, to be stated wherever this is used: an HMDA denial is not
a fall-through. Most denials occur before an offer is accepted, so the denial
rate is an UPPER bound on the probability that an accepted financed offer
collapses. pi* built from it is therefore an upper bound too, which makes the
resulting excess (pi - pi*) a LOWER bound - the conservative direction for a
paper arguing the excess is large, and the honest one to report.
"""
import urllib.request, urllib.parse, json, time

B = "https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations?"
NYC = ["36005", "36047", "36061", "36081", "36085"]   # Bronx, Kings, New York, Queens, Richmond
YEARS = ["2019", "2020", "2021", "2022", "2023"]


def get(params, tries=6):
    u = B + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(u, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            print(f"   retry {i+1}: {str(e)[:60]}")
            time.sleep(3 * (i + 1))
    return None


def rate(agg):
    if not agg:
        return None
    d = {a["actions_taken"]: a["count"] for a in agg.get("aggregations", [])}
    o, dn = d.get("1", 0), d.get("3", 0)
    return dn / (o + dn) if (o + dn) else None


rows = []
print(f"{'year':>6} {'NYC denial':>12} {'US denial':>11} {'ratio':>7}")
for y in YEARS:
    base = {"years": y, "actions_taken": "1,3", "loan_purposes": "1"}
    nyc = rate(get({**base, "counties": ",".join(NYC)}))
    us = rate(get({**base, "states": ",".join([
            "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY",
            "LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND",
            "OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"])}))
    if nyc and us:
        rows.append(dict(year=y, nyc=nyc, us=us, ratio=nyc / us))
        print(f"{y:>6} {nyc*100:11.2f}% {us*100:10.2f}% {nyc/us:7.2f}")
    else:
        print(f"{y:>6}   query failed  nyc={nyc} us={us}")

if rows:
    r = sum(x["ratio"] for x in rows) / len(rows)
    print(f"\n   mean NYC / US denial-rate ratio: {r:.2f}")
    print(f"\n   Scaling Reher and Valkanov's national pi*:")
    for lab, v in [("representative seller (3.3%)", 0.033), ("with local heterogeneity (6.9%)", 0.069)]:
        print(f"      {lab:<34} -> pi*_NYC = {v*r*100:.1f}%")
    json.dump({"rows": rows, "ratio": r,
               "pi_star_nyc_low": 0.033 * r, "pi_star_nyc_high": 0.069 * r},
              open("hmda_results.json", "w"), indent=1)
    print("\nwrote hmda_results.json")
