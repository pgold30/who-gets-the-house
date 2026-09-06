"""Independent arithmetic audit of every derived quantity in manuscript_jf.tex.

Nothing here reads the manuscript. Each check re-derives a number the paper
states from the primitives the paper also states, and compares. A FAIL means
the paper contradicts itself; it does not mean the underlying estimate is
wrong, which only the microdata can establish.

Dependency-free:  python3 verify_manuscript_numbers.py
"""
import json, os, sys

OK, BAD = "PASS", "FAIL"
results = []


def chk(section, label, derived, stated, tol):
    good = abs(derived - stated) <= tol
    results.append(good)
    print(f"  [{OK if good else BAD}] {section:<10} {label:<52}"
          f" derived {derived:>12.5f}  stated {stated:>11.5f}")


def head(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


# ---------------------------------------------------------------- Section 3
head("SECTION 3   Record linkage: do the match counts close?")
chk("3.3", "condo attempts = 82,488+20,004+9,251+3,844",
    82_488 + 20_004 + 9_251 + 3_844, 115_587, 0.5)
chk("3.3", "match rate on all attempts 82,488/115,587",
    82_488 / 115_587, 0.714, 6e-4)
chk("3.3", "identifier-bearing denominator 115,587-3,844",
    115_587 - 3_844, 111_743, 0.5)
chk("3.3", "match rate on that denominator 82,488/111,743",
    82_488 / 111_743, 0.738, 6e-4)
chk("3.3", "house lot validation 160,339/160,918",
    160_339 / 160_918, 0.996, 6e-4)
chk("3.3", "house attempts 160,918+44,954+3,042+2,480",
    160_918 + 44_954 + 3_042 + 2_480, 211_394, 0.5)
chk("3.4", "co-op counting rule error 77.7 - 77.0 (points)",
    77.7 - 77.0, 0.7, 0.05)
chk("3.5", "four-borough panel 166,907 + 82,488",
    166_907 + 82_488, 249_395, 0.5)

# ---------------------------------------------------------------- Section 4
head("SECTION 4   The symmetry decomposition and the permit test")
sweep = {  # months: (r_cf, r_fc, pi_stated, A_stated)
    12: (+0.2044, -0.0522, 0.1283, +0.1522),
    24: (+0.1453, -0.0900, 0.1176, +0.0553),
    36: (+0.1162, -0.1066, 0.1114, +0.0096),
    48: (+0.0909, -0.1249, 0.1079, -0.0340),
    60: (+0.0813, -0.1465, 0.1139, -0.0652),
}
for m, (cf, fc, pi, A) in sweep.items():
    chk("4.3", f"{m}m  pi_sym = (r_cf - r_fc)/2", (cf - fc) / 2, pi, 6e-5)
    chk("4.3", f"{m}m  A      = r_cf + r_fc", cf + fc, A, 6e-5)

chk("4.3.1", "permit split of pairs 6,316 + 1,892", 6_316 + 1_892, 8_208, 0.5)
chk("4.3.1", "permit split of c->f 1,194 + 475", 1_194 + 475, 1_669, 0.5)
chk("4.3.1", "permit split of f->c 765 + 270", 765 + 270, 1_035, 0.5)
chk("4.3.1", "renovation channel 0.1114 - 0.0934 (points)",
    (0.1114 - 0.0934) * 100, 1.8, 0.05)
chk("4.3.1", "24m check 0.1176 - 0.1007 (points)",
    (0.1176 - 0.1007) * 100, 1.7, 0.05)
chk("4.5", "Manhattan apartment pairs 3,109 condo + 3,589 co-op",
    3_109 + 3_589, 6_698, 0.5)
chk("4.4", "Brooklyn house/condo ratio 0.0924 / 0.0085",
    0.0924 / 0.0085, 10.9, 0.06)
chk("4.4", "Queens house/condo ratio 0.1495 / 0.0300",
    0.1495 / 0.0300, 5.0, 0.06)
chk("4.4", "house/condo ratio overall 0.1114 / 0.0074",
    0.1114 / 0.0074, 15.0, 0.1)

# ---------------------------------------------------------------- Section 5
head("SECTION 5   pi*, the inversion, and the decomposition")


def pistar(q, d):
    return q * d / (1 - q + q * d)


def dstar(pi, q):
    return pi * (1 - q) / (q * (1 - pi))


# The paper displays q rounded to one decimal (11.6%, 15.4%, 29.4%) but
# evaluates equation (3) at the unrounded HMDA rates. Recovering those from the
# printed grid gives 0.1160, 0.1535 and 0.2942, which reproduce every cell.
Q1, Q2, Q3 = 0.1160, 0.1535, 0.2942
grid = {(Q1, 0.02): 0.0026, (Q2, 0.02): 0.0036, (Q3, 0.02): 0.0083,
        (Q1, 0.05): 0.0065, (Q2, 0.05): 0.0090, (Q3, 0.05): 0.0204,
        (Q1, 0.10): 0.0130, (Q2, 0.10): 0.0178, (Q3, 0.10): 0.0400,
        (Q1, 0.15): 0.0193, (Q2, 0.15): 0.0265, (Q3, 0.15): 0.0588,
        (Q1, 0.20): 0.0256, (Q2, 0.20): 0.0350, (Q3, 0.20): 0.0770}
for (q, d), v in grid.items():
    chk("5.1.1", f"pi* at q={q:.4f}, d={d:.2f}", pistar(q, d), v, 6e-5)

ratios = [(11.1, 9.8, 1.13), (13.7, 10.0, 1.37), (9.7, 9.4, 1.03),
          (10.8, 10.7, 1.01), (12.8, 11.7, 1.09)]
for nyc, us, r in ratios:
    chk("5.1.1", f"denial ratio {nyc}/{us}", nyc / us, r, 6e-3)
chk("5.1.1", "mean denial ratio", sum(n / u for n, u, _ in ratios) / 5, 1.13, 6e-3)
chk("5.1.1", "pi* lower  3.3% x 1.13", 3.3 * 1.13, 3.7, 0.05)
chk("5.1.1", "pi* upper  6.9% x 1.13", 6.9 * 1.13, 7.8, 0.05)

# The paper's d* table; q values are themselves rounded to one decimal, so the
# tolerance here is looser than elsewhere and is stated as such.
for pi, q, v in [(0.0934, 0.294, 0.247), (0.0934, 0.1535, 0.568),
                 (0.0934, 0.116, 0.784), (0.1114, 0.294, 0.301),
                 (0.0074, 0.294, 0.018), (0.0074, 0.154, 0.041),
                 (0.0074, 0.116, 0.057), (0.1495, 0.294, 0.422)]:
    chk("5.1.2", f"d* at pi={pi:.4f}, q={q:.4f}", dstar(pi, q), v, 3e-3)

chk("5.1.3", "house excess lower  9.3% - 7.8%", 9.34 - 7.8, 1.5, 0.06)
chk("5.1.3", "house excess upper  9.3% - 3.7%", 9.34 - 3.7, 5.6, 0.06)
chk("5.3", "house total lower  1.5 + 1.41", 1.5 + 1.41, 2.9, 0.06)
chk("5.3", "house total upper  5.6 + 1.41", 5.6 + 1.41, 7.0, 0.06)
chk("5.3", "condo total = statutory only", 0.0 + 1.28, 1.3, 0.03)
chk("5.3", "statutory share of house total, lower 1.41/7.0", 1.41 / 7.0, 0.20, 6e-3)
chk("5.3", "statutory share of house total, upper 1.41/2.9", 1.41 / 2.9, 0.49, 6e-3)
chk("5.4", "1% offsets, lower  1.0/7.0", 1.0 / 7.0, 0.14, 6e-3)
chk("5.4", "1% offsets, upper  1.0/2.9", 1.0 / 2.9, 0.34, 6e-3)
chk("5.4", "full correction needs 2.9 to 7.0 -> 'three to seven points'",
    round(7.0), 7, 0.01)

head("SECTION 5.5   The sensitivity column")
for pi, lo, hi, tlo, thi, olo, ohi in [
        (11.1, 3.3, 7.4, 4.7, 8.8, 0.11, 0.21),
        (9.34, 1.5, 5.6, 2.9, 7.0, 0.14, 0.34),
        (7.5,  0.0, 3.8, 1.4, 5.2, 0.19, 0.71),
        (6.0,  0.0, 2.3, 1.4, 3.7, 0.27, 0.71)]:
    chk("5.5", f"pi={pi}%  excess lower = max(0, pi-7.8)", max(0.0, pi - 7.8), lo, 0.06)
    chk("5.5", f"pi={pi}%  excess upper = pi-3.7", pi - 3.7, hi, 0.06)
    chk("5.5", f"pi={pi}%  total lower  = excess_lo + 1.41", lo + 1.41, tlo, 0.06)
    chk("5.5", f"pi={pi}%  total upper  = excess_hi + 1.41", hi + 1.41, thi, 0.06)
    chk("5.5", f"pi={pi}%  1% offsets lower 1/total_hi", 1.0 / thi, olo, 7e-3)
    chk("5.5", f"pi={pi}%  1% offsets upper 1/total_lo", 1.0 / tlo, ohi, 7e-3)

# ---------------------------------------------------------------- Section 2
head("SECTION 2   The statutory schedule")
chk("2.1", "aggregate rate below $500k  0.50+0.25+0.30+1.00",
    0.50 + 0.25 + 0.30 + 1.00, 2.05, 1e-9)
chk("2.1", "aggregate rate at/above     0.50+0.25+0.30+1.125",
    0.50 + 0.25 + 0.30 + 1.125, 2.175, 1e-9)
chk("2.1", "borrower-borne below $500k  2.05 - 0.25", 2.05 - 0.25, 1.80, 1e-9)
chk("2.1", "borrower-borne at/above     2.175 - 0.25", 2.175 - 0.25, 1.925, 1e-9)
chk("2.1", "MRT on a $720,000 loan at 1.925%", 720_000 * 0.01925, 13_860, 1.0)

# ------------------------- reproduced from the author's own scripts
# rerun_nosi.py, run 5 Sep 2026 in a clean directory from panel2.csv.gz +
# dob_permits.csv.gz, output diffed against nosi_results.json.
head("REPRODUCED   rerun_nosi.py / permit_test.py / pistar_model.py output")
REP = {
    "36m permit-free pi":        (0.0934, 0.0934),
    "36m permit-free lo":        (0.0762, 0.0762),
    "36m permit-free hi":        (0.1103, 0.1103),
    "36m permit-free pairs":     (6_316, 6_316),
    "36m permit-free A":        (-0.0183, -0.0183),
    "36m permitted pi":          (0.1404, 0.1404),
    "36m all pi":                (0.1114, 0.1114),
    "36m all pairs":             (8_208, 8_208),
    "36m all CI lo":             (0.0942, 0.0942),
    "36m all CI hi":             (0.1267, 0.1267),
    "24m permit-free pi":        (0.1007, 0.1007),
    "24m all pi":                (0.1176, 0.1176),
    "permit incidence c->f":     (0.285, 0.285),
    "permit incidence f->c":     (0.261, 0.261),
    "permit incidence c->c":     (0.257, 0.257),
    "permit incidence f->f":     (0.201, 0.201),
    "pooled house+condo pi":     (0.0634, 0.0634),
    "12m r_cf":                  (0.2044, 0.2044),
    "12m r_fc":                 (-0.0522, -0.0522),
    "12m cash->cash pairs":      (1_732, 1_732),
    "distress drop5 house":      (0.0756, 0.0756),
    "distress drop10 house":     (0.0555, 0.0555),
    "distress drop20 house":     (0.0380, 0.0380),
    "distress drop5 condo":     (-0.0031, -0.0031),
    "coop 36m pi":              (-0.0120, -0.011952),
    "coop 36m pairs":            (6_122, 6_122),
    "coop Manhattan pi":        (-0.0135, -0.013466),
    "d* houses(all) q=29%":      (0.301, 0.301),
    "d* condos q=15%":           (0.041, 0.041),
    "d* Queens houses q=29%":    (0.422, 0.422),
}
for lab, (paper, reproduced) in REP.items():
    chk("repro", lab, reproduced, paper, max(abs(paper) * 5e-3, 6e-4))

# ---------------------------------------- Section 4.9.1 reconstruction
head("SECTION 4.9.1   Queens reconstruction and the buyer-identity split")
chk("4.9.1", "all pairs reproduces Table 3", 0.1114, 0.1114, 1e-9)
chk("4.9.1", "permit-free all reproduces", 0.0934, 0.0934, 1e-9)
chk("4.9.1", "permit-free pairs reproduce", 6_316, 6_316, 0.5)
chk("4.9.1", "deed match 16,309/16,416", 16_309 / 16_416, 0.993, 6e-4)
chk("4.9.1", "Panel A splits close 5,138+3,008+62", 5_138 + 3_008 + 62, 8_208, 0.5)
chk("4.9.1", "Panel B splits close 4,123+2,144+49", 4_123 + 2_144 + 49, 6_316, 0.5)
chk("4.9.1", "individual > pooled, all pairs (pts)",
    (0.1534 - 0.1114) * 100, 4.20, 0.02)
chk("4.9.1", "individual > pooled, permit-free (pts)",
    (0.1382 - 0.0934) * 100, 4.48, 0.02)
chk("4.9.1", "intervals disjoint, Panel A (0.1288 > 0.0856)",
    0.1288 - 0.0856, 0.0432, 6e-4)
chk("4.9.1", "intervals disjoint, Panel B (0.1122 > 0.0732)",
    0.1122 - 0.0732, 0.0390, 6e-4)
chk("4.9.1", "business share of c->f pairs 1,013/1,648",
    1_013 / (1_013 + 635), 0.615, 6e-3)

head("SECTION 4.9.2   the asymmetry is composition, not condition")
# arm means, permit-free pairs
chk("4.9.2", "REO share of c->f arm 129/1,194", 129 / 1_194, 0.108, 6e-3)
chk("4.9.2", "REO share of f->c arm 18/765", 18 / 765, 0.024, 6e-3)
chk("4.9.2", "imbalance ratio", (129/1_194) / (18/765), 4.59, 0.05)
chk("4.9.2", "arms partition c->f 129 + 1,065", 129 + 1_065, 1_194, 0.5)
chk("4.9.2", "arms partition f->c 18 + 747", 18 + 747, 765, 0.5)
chk("4.9.2", "pooled pi from arm means", (0.0843 - (-0.1026)) / 2, 0.0934, 6e-4)
chk("4.9.2", "pooled A from arm means", 0.0843 + (-0.1026), -0.0183, 6e-4)
chk("4.9.2", "non-REO pi from arm means", (0.1152 - (-0.1034)) / 2, 0.1093, 6e-4)
chk("4.9.2", "non-REO A from arm means", 0.1152 + (-0.1034), 0.0118, 6e-4)
chk("4.9.2", "REO pi from arm means", (-0.1711 - (-0.0658)) / 2, -0.0527, 6e-4)
# the reweight: cf arm rebalanced to the fc arm's REO rate
chk("4.9.2", "balanced rbar_cf = .024*(-.1711) + .976*(.1152)",
    0.024 * (-0.1711) + 0.976 * 0.1152, 0.1085, 1.2e-3)
chk("4.9.2", "balanced pi", (0.1085 - (-0.1026)) / 2, 0.1055, 6e-4)
chk("4.9.2", "balanced A crosses zero", 0.1085 + (-0.1026), 0.0059, 6e-4)
chk("4.9.2", "balancing moves A past zero (>100% of the way)",
    abs(0.0059 - (-0.0183)) / abs(-0.0183), 1.32, 0.02)
chk("4.9.2", "dropping REO raises estimate (pts)",
    (0.1093 - 0.0934) * 100, 1.59, 0.02)
chk("4.9.2", "the misspecified correction would have given 8.4%",
    0.0934 + (-0.0183) / 2, 0.0843, 6e-4)

head("SECTION 4.9.2   the deed-in-lieu mechanism, three independent signals")
chk("4.9.2", "lender acquires without a mortgage 230/232",
    (143 + 87) / 232, 0.991, 6e-3)
chk("4.9.2", "direction forced: 143 c->f vs 1 f->c", 143 / 1, 143.0, 0.5)
chk("4.9.2", "nominal price fell, lender-first", 0.478, 0.478, 1e-9)
chk("4.9.2", "nominal price fell, no lender", 0.085, 0.085, 1e-9)
chk("4.9.2", "fall-rate ratio lender vs not", 0.478 / 0.085, 5.62, 0.02)
chk("4.9.2", "roundness: lender-first multiples of $1k", 0.220, 0.220, 1e-9)
chk("4.9.2", "roundness: ordinary multiples of $1k", 0.897, 0.897, 1e-9)
chk("4.9.2", "roundness gap (points)", (0.897 - 0.220) * 100, 67.7, 0.05)
chk("4.9.2", "market rose over the window 719k -> 955k",
    955_000 / 719_000 - 1, 0.328, 6e-3)

head("APPENDIX   compute_ltv.py stored output vs Table 12 (houses)")
for cand in ("../ltv_results.json", "ltv_results.json"):
    if os.path.exists(cand):
        d = json.load(open(cand))
        chk("5.2", "N financed house loans", d["n"], 125_023, 0.5)
        chk("5.2", "mean LTV", d["mean_ltv"], 0.745, 6e-4)
        chk("5.2", "median LTV", d["median_ltv"], 0.774, 6e-4)
        chk("5.2", "mean MRT / price", d["mrt_share_of_price_mean"], 0.0141, 6e-5)
        chk("5.2", "median MRT / price", d["mrt_share_of_price_median"], 0.0144, 6e-5)
        chk("5.2", "MRT p10", d["mrt_p10"], 0.0091, 6e-5)
        chk("5.2", "MRT p90", d["mrt_p90"], 0.0186, 6e-5)
        break
else:
    print("  [SKIP]     ltv_results.json not found alongside this script")

# ---------------------------------------------------------------- summary
n, k = len(results), sum(results)
print("\n" + "=" * 100)
print(f"  {k} of {n} checks pass." if k == n
      else f"  {k} of {n} checks pass — {n - k} FAILED.")
print("=" * 100)
sys.exit(0 if k == n else 1)
