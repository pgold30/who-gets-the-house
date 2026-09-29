"""Conditional stress test of the house contrast to hidden purchase mortgages (v3.4).

The instrument review (cross_ai_review.py) found a purchase mortgage behind 4
of 50 cash-labelled endpoints: 3 of the 20 sampled pairs in the
financed-to-cash arm under the lenient coding (2 of 20 if the two-lot
development loan H050-z is left unresolved), and none of the 20 in the
cash-to-financed arm. This script asks how far the contrast would move if
similar errors existed elsewhere.

Baseline: the corrected headline sample of Appendix G (the four pairs with a
documented error removed; 9.40 log points). All 53 reviewed pairs keep their
labels. In each draw a share q_fc of the unreviewed financed-to-cash pairs has
its cash endpoint recoded to financed, and a share q_cf of the unreviewed
cash-to-financed pairs likewise. Each pair in a switching arm has exactly one
cash-labelled endpoint, so arm-specific shares are the natural unit. The same
recoded data are fitted with and without same-surname pairs, so the two
estimates and their difference are paired within a draw.

The rates are assumed scenarios informed by the detected shares, not measured
error prevalence: 0.10 and 0.15 are the strict and lenient detected shares in
the financed-to-cash arm, 0.36 is the Wilson upper limit of 3 of 20, and 0.16
that of 0 of 20. Recoding is random within an arm and goes only in the
direction the review can detect; financed labels that are really cash cannot
be established from the documents. The ranges reported are the 2.5-97.5
percentiles of point estimates across draws, not confidence intervals.

Writes results/financing_stress_test.json, paper/generated/stress.tex and
paper/generated/stress_numbers.tex.
"""
import csv, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code")); sys.path.insert(0, str(ROOT / "inputs/3_section4.9"))
import analyze_repeat_sales as ars  # noqa: E402

SEED, DRAWS, CHUNKS = 20260930, 200, 8
QFC, QCF = (0.10, 0.15, 0.36), (0.0, 0.08, 0.16)
ERRORS = ("H024", "H032", "H034", "H050")


def load():
    d = pd.read_csv(ROOT / "data/house_pairs_enriched.csv.gz",
                    dtype={"bbl": str, "borough": str, "zipcode": str, "cd": str, "deed_a": str, "deed_z": str})
    G = int(d.cluster.max() + 1)
    for c in ("permit_free", "lender_high", "geo_linked"):
        d[c] = d[c].astype(str).str.lower().isin(["true", "1"])
    d = d[d.permit_free & ~d.lender_high & d.geo_linked].copy().reset_index(drop=True)
    for s in "az":
        d["date_" + s] = pd.to_datetime(d["date_" + s]).dt.date
    d["zipcode"] = d["zipcode"].fillna("").str.replace(r"\.0$", "", regex=True)
    assert len(d) == 6006
    rel = pd.read_csv(ROOT / "results/related_party_flags.csv", dtype={"bbl": str, "deed_a": str, "deed_z": str})
    assert len(rel) == 6006 and (rel.bbl.values == d.bbl.values).all()
    for s in ("deed_a", "deed_z"):
        assert (rel[s].fillna("").values == d[s].fillna("").values).all()
    d["related"] = (rel.related_a.astype(int) + rel.related_z.astype(int)).values > 0
    # locate every reviewed pair by parcel and both frozen sale dates
    rows = {}
    for r in csv.DictReader(open(ROOT / "audit/focused_blinded_house_review.csv", newline="")):
        rows.setdefault(r["case_id"], {})[r["endpoint"]] = r
    case = {}
    for c, e in rows.items():
        m = (d.bbl == e["a"]["bbl"]) & (d.date_a.astype(str) == e["a"]["sale_date"]) & (d.date_z.astype(str) == e["z"]["sale_date"])
        case[c] = np.flatnonzero(m.values)
    assert len(case) == 53 and all(len(v) == 1 for v in case.values()), "each reviewed pair must match one row"
    d["reviewed"] = False
    d.loc[[int(v[0]) for v in case.values()], "reviewed"] = True
    base = d.drop(index=[int(case[c][0]) for c in ERRORS]).reset_index(drop=True)
    return base, G


def fit(e, G):
    r, *_ = ars.estimate(e, ars.design(e, "zipcode", True), G)
    return r


def _draws(args):
    qfc, qcf, seed, n = args
    d, G = load()
    rng = np.random.default_rng(seed)
    fa, fz, rv = d.financed_base_a.to_numpy(), d.financed_base_z.to_numpy(), d.reviewed.to_numpy()
    fc = np.flatnonzero((fa == 1) & (fz == 0) & ~rv)
    cf = np.flatnonzero((fa == 0) & (fz == 1) & ~rv)
    out = []
    for _ in range(n):
        e = d.copy()
        e.loc[rng.choice(fc, int(round(qfc * len(fc))), replace=False), "financed_base_z"] = 1
        e.loc[rng.choice(cf, int(round(qcf * len(cf))), replace=False), "financed_base_a"] = 1
        full = 100 * fit(e, G)["pi_joint"]
        norel = 100 * fit(e[~e.related].reset_index(drop=True), G)["pi_joint"]
        out.append((full, norel))
    return out


def main():
    d, G = load()
    b_all, b_nr = fit(d, G), fit(d[~d.related].reset_index(drop=True), G)
    base = {"pairs": int(b_all["pairs"]), "full": 100 * b_all["pi_joint"], "full_ci": [100 * x for x in b_all["ci_joint"]],
            "pairs_no_related": int(b_nr["pairs"]), "no_related": 100 * b_nr["pi_joint"],
            "no_related_ci": [100 * x for x in b_nr["ci_joint"]]}
    assert round(base["full"], 2) == 9.40 and base["pairs"] == 6002
    fa, fz, rv = d.financed_base_a.to_numpy(), d.financed_base_z.to_numpy(), d.reviewed.to_numpy()
    arms = {"fc_unreviewed": int(((fa == 1) & (fz == 0) & ~rv).sum()), "cf_unreviewed": int(((fa == 0) & (fz == 1) & ~rv).sum()),
            "reviewed_kept_fixed": int(rv.sum())}
    cells = [(qfc, qcf) for qfc in QFC for qcf in QCF]
    jobs = [(qfc, qcf, SEED + 100 * i + k, DRAWS // CHUNKS) for i, (qfc, qcf) in enumerate(cells) for k in range(CHUNKS)]
    with ProcessPoolExecutor(8) as ex:
        outs = list(ex.map(_draws, jobs))
    res = {}
    for (qfc, qcf, _, _), o in zip(jobs, outs):
        res.setdefault((qfc, qcf), []).extend(o)
    pct = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    sim = {}
    for (qfc, qcf), v in res.items():
        a = np.array(v)
        full, nr, gap = a[:, 0], a[:, 1], a[:, 0] - a[:, 1]
        sim[f"q_fc={qfc}|q_cf={qcf}"] = {"draws": len(a), "full_mean": float(full.mean()), "full_range": pct(full),
                                         "no_related_mean": float(nr.mean()), "no_related_range": pct(nr),
                                         "share_removed_by_screen_mean": float((gap / full).mean()),
                                         "share_removed_range": pct(gap / full),
                                         "min_full": float(full.min()), "min_no_related": float(nr.min())}
    out = {"seed": SEED, "draws_per_cell": DRAWS, "baseline": base, "arms": arms, "cells": sim, "note": __doc__}
    (ROOT / "results/financing_stress_test.json").write_text(json.dumps(out, indent=1) + "\n")

    f2 = lambda x: f"{x:.2f}"
    rng2 = lambda r: f"[{f2(r[0])}, {f2(r[1])}]"
    lab = {0.10: "0.10 (2 of 20)", 0.15: "0.15 (3 of 20)", 0.36: "0.36 (upper limit)"}
    lines = [r"\begin{table}[htbp]\centering\caption{Conditional stress test: random recoding of unreviewed cash labels}\label{tab:stress}",
             r"\footnotesize\setlength{\tabcolsep}{3.5pt}\begin{tabular}{llccc}\toprule",
             r"Share recoded, & Share recoded, & All pairs & Without same- & Share of contrast \\",
             r"financed-to-cash arm & cash-to-financed arm & & surname pairs & removed by screen \\\midrule",
             rf"\multicolumn{{2}}{{l}}{{Corrected baseline, no recoding}} & {f2(base['full'])} & {f2(base['no_related'])} & {100 * (1 - base['no_related'] / base['full']):.0f}\% \\\addlinespace"]
    for (qfc, qcf) in cells:
        s = sim[f"q_fc={qfc}|q_cf={qcf}"]
        lines.append(rf"{lab[qfc]} & {qcf:.2f} & {f2(s['full_mean'])} {rng2(s['full_range'])} & {f2(s['no_related_mean'])} {rng2(s['no_related_range'])} & "
                     rf"{100 * s['share_removed_by_screen_mean']:.0f}\% [{100 * s['share_removed_range'][0]:.0f}, {100 * s['share_removed_range'][1]:.0f}] \\")
    lines += [r"\bottomrule\end{tabular}",
              rf"\notes{{Headline joint model, log points. Baseline: the {base['pairs']:,} pairs left after removing the four pairs with a documented label error (Appendix~\ref{{sec:focusedvalidation}}); {base['pairs_no_related']:,} without same-surname pairs. "
              rf"Each draw recodes, at random, the stated share of the {arms['fc_unreviewed']:,} unreviewed financed-to-cash pairs and of the {arms['cf_unreviewed']:,} unreviewed cash-to-financed pairs from cash to financed at their cash endpoint; the {arms['reviewed_kept_fixed']} reviewed pairs keep their labels. "
              rf"Both columns are fitted on the same recoded data. Entries are means over {DRAWS} draws, with the 2.5th and 97.5th percentiles of the point estimates in brackets; these are scenario ranges, not confidence intervals. "
              r"Shares are assumed scenarios informed by the review's detected discrepancies (2 of 20 under the strict coding, 3 of 20 under the lenient one; 0.36 and 0.16 are Wilson upper limits), not measured error rates. \texttt{code/financing\_stress\_test.py}.}",
              r"\end{table}"]
    (ROOT / "paper/generated/stress.tex").write_text("\n".join(lines) + "\n")
    worst = sim["q_fc=0.36|q_cf=0.16"]
    mac = {"StressBase": f2(base["full"]), "StressBaseNoRel": f2(base["no_related"]),
           "StressWorstFull": f2(worst["full_mean"]), "StressWorstFullLow": f2(worst["full_range"][0]),
           "StressWorstNoRel": f2(worst["no_related_mean"]), "StressWorstNoRelLow": f2(worst["no_related_range"][0]),
           "StressMinNoRel": f2(min(s["min_no_related"] for s in sim.values())),
           "StressShareLow": f"{100 * min(s['share_removed_by_screen_mean'] for s in sim.values()):.0f}",
           "StressShareHigh": f"{100 * max(s['share_removed_by_screen_mean'] for s in sim.values()):.0f}",
           "StressFullMeanLow": f2(min(s["full_mean"] for s in sim.values())), "StressFullMeanHigh": f2(max(s["full_mean"] for s in sim.values())),
           "StressNoRelMeanLow": f2(min(s["no_related_mean"] for s in sim.values())), "StressNoRelMeanHigh": f2(max(s["no_related_mean"] for s in sim.values())),
           "StressReviewedFixed": str(arms["reviewed_kept_fixed"]),
           "StressFCArm": f"{arms['fc_unreviewed']:,}", "StressCFArm": f"{arms['cf_unreviewed']:,}", "StressDraws": str(DRAWS)}
    (ROOT / "paper/generated/stress_numbers.tex").write_text("".join(rf"\newcommand{{\{k}}}{{{v}}}" + "\n" for k, v in mac.items()))
    print(json.dumps({"baseline": base, "arms": arms}, indent=1))
    for k, s in sim.items():
        print(f"{k:22s} full {s['full_mean']:6.2f} {rng2(s['full_range'])}  no-rel {s['no_related_mean']:5.2f} {rng2(s['no_related_range'])}  "
              f"removed {100 * s['share_removed_by_screen_mean']:.0f}%  min no-rel {s['min_no_related']:.2f}")


if __name__ == "__main__":
    main()
