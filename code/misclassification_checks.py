"""Financing-label errors beyond random one-direction recoding (v3.5).

The stress test of v3.4 (financing_stress_test.py) recodes, at random and in
one direction, cash labels inside the two switching arms. This script relaxes
each of those restrictions on the same corrected sample (the 6,002 pairs left
after the four documented label errors; the 49 other reviewed pairs keep their
reviewed labels).

1. Both directions, whole sample. A share h of unreviewed cash-labelled sale
   endpoints is recoded to financed (a hidden purchase mortgage) and a share f
   of unreviewed financed-labelled endpoints to cash (a recorded loan that did
   not finance the purchase). Every pair is eligible, so cash-cash and
   financed-financed pairs can become switching pairs and switching pairs can
   leave their arm; the arms are rebuilt from the recoded labels. h = 0.08 is
   the review's detected share (4 of 50 cash endpoints) and 0.188 its 95%
   upper limit. f = 0.036 counts the two unresolved financed endpoints as
   errors (2 of 56) and 0.064 is the Wilson upper limit for 0 of 56. At most
   one endpoint per pair is recoded.
2. Outcome-correlated errors. Each possible recoding moves the contrast in a
   known direction given the pair's residual growth r (log growth net of the
   headline model's time and location effects): a pair that enters the
   cash-to-financed arm lowers the contrast if r is low, one that leaves it
   lowers the contrast if r is high, and the reverse for the financed-to-cash
   arm. "Adversarial" recodes the h and f shares with the largest such effect,
   against the contrast (and, for the other bound, in its favour). "Tilted"
   draws them with probability proportional to exp(kappa x standardized
   effect); a sweep over kappa finds the strength of correlation at which the
   contrast reaches zero, reported as the mean standardized effect of the
   recoded labels (0 = unrelated to growth). Adversarial selection is a stress
   bound, not a plausible error process.
3. Documented failure modes. The review's four errors were two index-date
   errors and two loans recorded against two adjoining lots. "Late or early
   recording" recodes to financed every unreviewed cash endpoint that has a
   mortgage in the wide window (15 days before to 180 after) but not in the
   base window. "Company buyers" draws the h share of hidden mortgages only
   from cash endpoints whose buyer is a company, where development and
   blanket loans are common.

Each recoded sample is fitted with and without same-surname pairs, paired
within a draw. Ranges are 2.5-97.5 percentiles of point estimates across 200
draws: scenario ranges, not confidence intervals.

4. Joint table. The published sample and the successive screens (documented
   errors, same-surname pairs, broad lender-name rule, legal-rule deeds from
   the companion classifier) on the paper's common parcel bootstrap (seed
   20260909, 999 multinomial draws over 8,127 parcel clusters), so every row
   and every difference is paired with the published estimate.

Writes results/misclassification_checks.json, paper/generated/misclass.tex,
paper/generated/jointscreens.tex and paper/generated/misclass_numbers.tex.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code")); sys.path.insert(0, str(ROOT / "inputs/3_section4.9"))
import analyze_repeat_sales as ars  # noqa: E402
import financing_stress_test as fst  # noqa: E402

SEED, DRAWS, CHUNKS = 20261001, 200, 8
H_RATES, F_RATES = (0.08, 0.188), (0.0, 0.036, 0.064)


def residual_growth(d):
    return ars.residualize(ars.design(d, "zipcode", True), d.y.to_numpy())


def candidates(d, r):
    """All single-endpoint recodings on unreviewed pairs, with their effect on the contrast.

    effect > 0 means the recoding lowers the contrast (against the finding)."""
    fa, fz, rv = d.financed_base_a.to_numpy(), d.financed_base_z.to_numpy(), d.reviewed.to_numpy()
    rows = []
    for i in np.flatnonzero(~rv):
        a, z = fa[i], fz[i]
        for end, lab in (("a", a), ("z", z)):
            na, nz = (1 - a, z) if end == "a" else (a, 1 - z)
            before = "cf" if (a, z) == (0, 1) else "fc" if (a, z) == (1, 0) else None
            after = "cf" if (na, nz) == (0, 1) else "fc" if (na, nz) == (1, 0) else None
            eff = 0.0
            if before == "cf": eff += r[i]      # removing a cash-to-financed pair with high r lowers it
            if before == "fc": eff -= r[i]      # removing a financed-to-cash pair with low r lowers it
            if after == "cf": eff -= r[i]       # adding a cash-to-financed pair with low r lowers it
            if after == "fc": eff += r[i]       # adding a financed-to-cash pair with high r lowers it
            rows.append((i, end, int(lab), eff))
    c = pd.DataFrame(rows, columns=["pair", "end", "label", "effect"])
    c["company"] = [bool(d[f"buyer_entity_{e}"].iat[i]) for i, e in zip(c.pair, c.end)]
    c["late"] = [(lab == 0) and bool(d[f"financed_wide_{e}"].iat[i]) for i, e, lab in zip(c.pair, c.end, c.label)]
    return c


def pick(c, n, rng, mode, sign=1.0, kappa=1.0):
    """Choose n recodings from candidate rows c (one label type), at most one per pair."""
    if n <= 0 or len(c) == 0:
        return c.iloc[:0]
    if mode == "random":
        order = rng.permutation(len(c))
    elif mode == "adversarial":
        order = np.argsort(-sign * c.effect.to_numpy(), kind="stable")
    elif mode == "tilted":
        e = sign * c.effect.to_numpy(); z = (e - e.mean()) / e.std()
        key = np.log(rng.random(len(c))) / np.exp(kappa * z)   # weighted sampling without replacement (Efraimidis-Spirakis)
        order = np.argsort(-key)
    out = c.iloc[order]
    out = out[~out.pair.duplicated()]
    return out.iloc[:n]


def apply(d, flips):
    e = d.copy()
    for end in "az":
        f = flips[flips.end == end]
        col = f"financed_base_{end}"
        e.loc[f.pair.to_numpy(), col] = 1 - e.loc[f.pair.to_numpy(), col].to_numpy()
    return e


def fit_pair(e, G):
    full = fst.fit(e, G)
    nr = fst.fit(e[~e.related].reset_index(drop=True), G)
    return 100 * full["pi_joint"], 100 * nr["pi_joint"], int(full["cf"]), int(full["fc"])


def scenario_draws(args):
    name, h, f, mode, sign, pool, seed, n = args
    d, G = fst.load()
    c = candidates(d, residual_growth(d))
    cash, fin = c[c.label == 0], c[c.label == 1]
    if pool == "company":
        cash = cash[cash.company]
    nh, nf = int(round(h * (c.label == 0).sum())), int(round(f * (c.label == 1).sum()))
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        fh = pick(cash, nh, rng, mode, sign)
        ff = pick(fin[~fin.pair.isin(fh.pair)], nf, rng, mode, sign)
        out.append(fit_pair(apply(d, pd.concat([fh, ff])), G) + (len(fh) + len(ff),))
    return name, out


KAPPAS, SWEEP_H, SWEEP_F, SWEEP_DRAWS = tuple(round(0.1 * k, 1) for k in range(11)), 0.08, 0.036, 96


def sweep_draws(args):
    kappa, seed, n = args
    d, G = fst.load()
    c = candidates(d, residual_growth(d))
    cash, fin = c[c.label == 0], c[c.label == 1]
    z = {lab: (g.effect - g.effect.mean()) / g.effect.std() for lab, g in ((0, cash), (1, fin))}
    nh, nf = int(round(SWEEP_H * len(cash))), int(round(SWEEP_F * len(fin)))
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        fh = pick(cash, nh, rng, "tilted", 1.0, kappa)
        ff = pick(fin[~fin.pair.isin(fh.pair)], nf, rng, "tilted", 1.0, kappa)
        zbar = float(np.concatenate([z[0].loc[fh.index].to_numpy(), z[1].loc[ff.index].to_numpy()]).mean())
        out.append(fit_pair(apply(d, pd.concat([fh, ff])), G)[:2] + (zbar,))
    return kappa, out


def crossing(xs, ys):
    """Linear interpolation of the first x at which y falls to zero."""
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if y0 > 0 >= y1:
            return x0 + (x1 - x0) * y0 / (y0 - y1)
    return None


SCENARIOS = []
for h in H_RATES:
    for f in F_RATES:
        SCENARIOS.append((f"random|h={h}|f={f}", h, f, "random", 1.0, "all"))
for h, f in ((0.08, 0.036), (0.188, 0.064)):
    SCENARIOS.append((f"tilted_against|h={h}|f={f}", h, f, "tilted", 1.0, "all"))
    SCENARIOS.append((f"tilted_for|h={h}|f={f}", h, f, "tilted", -1.0, "all"))
    SCENARIOS.append((f"adversarial_against|h={h}|f={f}", h, f, "adversarial", 1.0, "all"))
    SCENARIOS.append((f"adversarial_for|h={h}|f={f}", h, f, "adversarial", -1.0, "all"))
for h in H_RATES:
    SCENARIOS.append((f"company|h={h}|f=0.0", h, 0.0, "random", 1.0, "company"))


# ---------------------------------------------------------------- joint table
_S = {}


def _joint_draw(w):
    from robust_estimators import wls
    X, Q, y, samples = _S["X"], _S["Q"], _S["y"], _S["samples"]
    out = {}
    for name, m in samples.items():
        keep = m & (w > 0)
        b, _ = wls(X[keep], Q[keep], y[keep], w[keep])
        out[name] = 100 * .5 * (b[0] - b[1])
    return out


def joint_table():
    from robust_estimators import switches, multinomials
    from related_party import flags
    import legal_rule_screen as lrs
    d = pd.read_csv(ROOT / "data/house_pairs_enriched.csv.gz",
                    dtype={"bbl": str, "borough": str, "zipcode": str, "cd": str, "deed_a": str, "deed_z": str})
    G = int(d.cluster.max() + 1); assert G == 8127
    d = d[d.permit_free & ~d.lender_high & d.geo_linked].copy().reset_index(drop=True)
    for s in "az":
        d["date_" + s] = pd.to_datetime(d["date_" + s]).dt.date
    assert len(d) == 6006
    base, _ = fst.load()
    key = set(zip(base.bbl, base.date_a.astype(str), base.date_z.astype(str)))
    documented = ~np.array([k in key for k in zip(d.bbl, d.date_a.astype(str), d.date_z.astype(str))])
    assert documented.sum() == 4
    d, _ = flags(d)
    rel = ((d.related_a + d.related_z) > 0).to_numpy()
    broad = d.lender_broad.astype(str).str.lower().isin(["true", "1"]).to_numpy()
    ev = lrs.events(False)
    legal = (d.deed_a.map(ev).isin(lrs.acf.NONMARKET) | d.deed_z.map(ev).isin(lrs.acf.NONMARKET)).to_numpy()
    steps = [("published", np.ones(len(d), bool)),
             ("documented_errors_removed", ~documented)]
    steps.append(("plus_no_same_surname", steps[-1][1] & ~rel))
    steps.append(("plus_no_broad_lender_name", steps[-1][1] & ~broad))
    steps.append(("plus_no_legal_rule_deed", steps[-1][1] & ~legal))
    samples = dict(steps)
    X = ars.design(d, "zipcode", True); y = d.y.to_numpy(); Q = switches(d); cl = d.cluster.to_numpy()
    _S.update(X=X, Q=Q, y=y, samples=samples)
    point = _joint_draw(np.ones(len(d)))
    assert round(point["published"], 2) == 9.25 and round(point["documented_errors_removed"], 2) == 9.40
    t = time.monotonic()
    with get_context("fork").Pool(max(1, 8)) as pool:
        D = pd.DataFrame(pool.map(_joint_draw, [w[cl].astype(float) for w in multinomials(G, ars.SEED)], chunksize=8))
    published = json.loads((ROOT / "results/legal_rule_screen.json").read_text())["ci"]["all|ols"]
    assert np.allclose(np.percentile(D["published"], [2.5, 97.5]) / 100, published, atol=1e-7), "must reuse the published draws"
    names = [n for n, _ in steps]
    rows = []
    for k, n in enumerate(names):
        m = samples[n]
        rows.append({"step": n, "pairs": int(m.sum()), "cf": int((Q[m, 0] == 1).sum()), "fc": int((Q[m, 1] == 1).sum()),
                     "estimate": point[n], "ci": np.percentile(D[n], [2.5, 97.5]).tolist(),
                     "change_from_published": point[n] - point["published"],
                     "change_from_published_ci": np.percentile(D[n] - D["published"], [2.5, 97.5]).tolist(),
                     "change_from_previous": point[n] - point[names[k - 1]] if k else 0.0,
                     "change_from_previous_ci": np.percentile(D[n] - D[names[k - 1]], [2.5, 97.5]).tolist() if k else [0.0, 0.0]})
    return {"rows": rows, "bootstrap": {"draws": len(D), "seed": ars.SEED, "clusters": G, "seconds": time.monotonic() - t},
            "flag_counts": {"documented": int(documented.sum()), "same_surname": int(rel.sum()),
                            "broad_lender_name": int(broad.sum()), "legal_rule_deed": int(legal.sum())}}


def write_outputs(out):
    S, B, J = out["scenarios"], out["baseline"], out["joint_table"]
    f2 = lambda x: f"{x:.2f}"
    rg = lambda r: f"[{f2(r[0])}, {f2(r[1])}]"
    pc = lambda x: f"{100 * x:.0f}\\%"

    def row(label, s, show_range=True):
        full = f2(s["full_mean"]) + (f" {rg(s['full_range'])}" if show_range and s["draws"] > 1 else "")
        nr = f2(s["no_related_mean"]) + (f" {rg(s['no_related_range'])}" if show_range and s["draws"] > 1 else "")
        return rf"{label} & {s['recoded']:,.0f} & {s['cf_pairs']:,.0f} / {s['fc_pairs']:,.0f} & {full} & {nr} & {pc(s['share_removed_mean'])} \\"
    L = [r"\begin{table}[htbp]\centering\caption{Financing-label errors in both directions, across the whole sample and related to price growth}\label{tab:misclass}",
         r"\footnotesize\setlength{\tabcolsep}{2.2pt}\begin{tabular}{lccccc}\toprule",
         r"Scenario & Labels & Arms & All pairs & Without same- & Removed \\",
         r" & recoded & (c-to-f / f-to-c) & & surname pairs & by screen \\\midrule",
         rf"Corrected baseline, no recoding & 0 & {B['cf']:,} / {B['fc']:,} & {f2(B['full'])} & {f2(B['no_related'])} & {pc(1 - B['no_related'] / B['full'])} \\\addlinespace",
         r"\multicolumn{6}{l}{\textit{A. Random, both directions, all pairs}} \\"]
    for h, f in ((0.08, 0.0), (0.08, 0.036), (0.188, 0.0), (0.188, 0.064)):
        L.append(row(f"Hidden {100 * h:.1f}\\%, false financed {100 * f:.1f}\\%", S[f"random|h={h}|f={f}"]))
    L += [r"\addlinespace\multicolumn{6}{l}{\textit{B. Documented failure modes}} \\",
          row("Late or early recording, all", S["late_recording|all"]),
          row("Company buyers only, hidden 8.0\\%", S["company|h=0.08|f=0.0"]),
          row("Company buyers only, hidden 18.8\\%", S["company|h=0.188|f=0.0"]),
          r"\addlinespace\multicolumn{6}{l}{\textit{C. Related to growth, hidden 8.0\%, false financed 3.6\%}} \\"]
    rec = S["random|h=0.08|f=0.036"]["recoded"]
    for r in out["sweep"]:
        if r["kappa"] in (0.3, 0.5, 0.7, 1.0):
            L.append(rf"Mean standardized effect {r['recoded_effect_z']:.2f} & {rec:,.0f} & -- & {f2(r['full_mean'])} & {f2(r['no_related_mean'])} & -- \\")
    L += [row("Worst case against the contrast", S["adversarial_against|h=0.08|f=0.036"], False),
          row("Worst case in its favour", S["adversarial_for|h=0.08|f=0.036"], False),
          r"\bottomrule\end{tabular}",
          rf"\notes{{Headline joint model, log points, on the corrected sample of Table~\ref{{tab:stress}}; the {B['reviewed_fixed']} reviewed pairs keep their labels. "
          rf"Hidden: share of the {out['counts']['cash_endpoints']:,} unreviewed cash-labelled endpoints recoded to financed; false financed: share of the {out['counts']['financed_endpoints']:,} unreviewed financed-labelled endpoints recoded to cash; at most one endpoint per pair. "
          r"Arms are rebuilt after recoding. Panels A and B: means over 200 draws with the 2.5th and 97.5th percentiles of the point estimates; late or early recording recodes every cash endpoint with a mortgage in the wide but not the base window. "
          rf"Panel C draws the recoded labels with probability rising in their effect against the contrast; the first column gives the mean standardized effect of the labels recoded (0 when unrelated to growth), {out['breakdown']['draws_per_kappa']} draws each. "
          r"Worst cases pick the labels with the largest effect. Scenario ranges, not confidence intervals. \texttt{code/misclassification\_checks.py}.}",
          r"\end{table}"]
    gen = ROOT / "paper/generated"
    (gen / "misclass.tex").write_text("\n".join(L) + "\n")
    rows = {r["step"]: r for r in J["rows"]}
    lab = {"published": "Published headline sample", "documented_errors_removed": "Less the four documented label errors",
           "plus_no_same_surname": "\\quad and same-surname pairs", "plus_no_broad_lender_name": "\\quad and the broad lender-name rule",
           "plus_no_legal_rule_deed": "\\quad and legal-rule deeds"}
    T = [r"\begin{table}[htbp]\centering\caption{Documented corrections and screens applied together}\label{tab:jointscreens}",
         r"\footnotesize\setlength{\tabcolsep}{2.5pt}\begin{tabular}{lrccc}\toprule",
         r"Sample & Pairs & Contrast & Change from & Change from \\",
         r" & & [95\% CI] & published & row above \\\midrule"]
    for k, n in enumerate(lab):
        r = rows[n]
        T.append(rf"{lab[n]} & {r['pairs']:,} & {f2(r['estimate'])} {rg(r['ci'])} & "
                 + ("--" if not k else f"{r['change_from_published']:+.2f} {rg(r['change_from_published_ci'])}") + " & "
                 + ("--" if k < 2 else f"{r['change_from_previous']:+.2f} {rg(r['change_from_previous_ci'])}") + r" \\")
    T += [r"\bottomrule\end{tabular}",
          rf"\notes{{Headline joint model, log points. Each row removes the stated pairs from the row above. Intervals are 2.5th--97.5th percentiles over the paper's common parcel bootstrap ({J['bootstrap']['draws']} draws, seed {J['bootstrap']['seed']}), so every row and difference is paired with the published estimate. "
          rf"Flags in the published sample: {J['flag_counts']['same_surname']} same-surname pairs, {J['flag_counts']['broad_lender_name']} pairs matching the broad lender-name rule and {J['flag_counts']['legal_rule_deed']} pairs with a legal-rule deed (Section~\ref{{sec:who}}, Appendix~\ref{{sec:focusedvalidation}}). \texttt{{code/misclassification\_checks.py}}.}}",
          r"\end{table}"]
    (gen / "jointscreens.tex").write_text("\n".join(T) + "\n")
    rand = [S[k] for k in S if k.startswith("random|")]
    stable = rand + [S[k] for k in S if k.startswith(("company|", "late_recording|"))]
    br = out["breakdown"]
    last = rows["plus_no_legal_rule_deed"]
    m = {"MisCashEnds": f"{out['counts']['cash_endpoints']:,}", "MisFinEnds": f"{out['counts']['financed_endpoints']:,}",
         "MisRandLow": f2(min(s["full_mean"] for s in rand)), "MisRandHigh": f2(max(s["full_mean"] for s in rand)),
         "MisRandNoRelLow": f2(min(s["no_related_mean"] for s in rand)), "MisRandNoRelHigh": f2(max(s["no_related_mean"] for s in rand)),
         "MisShareLow": f"{100 * min(s['share_removed_mean'] for s in stable):.0f}", "MisShareHigh": f"{100 * max(s['share_removed_mean'] for s in stable):.0f}",
         "MisLate": f2(S["late_recording|all"]["full_mean"]), "MisLateN": f"{S['late_recording|all']['recoded']:.0f}",
         "MisCompanyLow": f2(min(S[k]["full_mean"] for k in S if k.startswith("company|"))),
         "MisCompanyHigh": f2(max(S[k]["full_mean"] for k in S if k.startswith("company|"))),
         "MisBreakFull": f"{br['full_zero_at_effect_z']:.2f}", "MisBreakNoRel": f"{br['no_related_zero_at_effect_z']:.2f}",
         "MisAdvAgainst": f2(S["adversarial_against|h=0.08|f=0.036"]["full_mean"]), "MisAdvFor": f2(S["adversarial_for|h=0.08|f=0.036"]["full_mean"]),
         "MisSweepRecoded": f"{S['random|h=0.08|f=0.036']['recoded']:,.0f}",
         "JointAll": f2(last["estimate"]), "JointAllCI": rg(last["ci"]), "JointAllPairs": f"{last['pairs']:,}",
         "JointAllChange": f"{last['change_from_published']:+.2f}", "JointAllChangeCI": rg(last["change_from_published_ci"]),
         "JointLegalStep": f"{last['change_from_previous']:+.2f}", "JointLegalStepCI": rg(last["change_from_previous_ci"]),
         "JointBroadStep": f"{rows['plus_no_broad_lender_name']['change_from_previous']:+.2f}",
         "JointDocChange": f"{rows['documented_errors_removed']['change_from_published']:+.2f}",
         "JointDocChangeCI": rg(rows["documented_errors_removed"]["change_from_published_ci"])}
    import re
    minus = lambda s: re.sub(r"(?<![-\w$])-(?=\d)", "$-$", s)
    (gen / "misclass_numbers.tex").write_text("".join(rf"\newcommand{{\{k}}}{{{minus(v)}}}" + "\n" for k, v in m.items()))
    for name in ("misclass.tex", "jointscreens.tex"):
        (gen / name).write_text(minus((gen / name).read_text()))


def main():
    if "--outputs-only" in sys.argv:
        write_outputs(json.loads((ROOT / "results/misclassification_checks.json").read_text()))
        return
    d, G = fst.load()
    b_full, b_nr, b_cf, b_fc = fit_pair(d, G)
    assert round(b_full, 2) == 9.40
    c = candidates(d, residual_growth(d))
    counts = {"cash_endpoints": int((c.label == 0).sum()), "financed_endpoints": int((c.label == 1).sum()),
              "company_cash_endpoints": int(((c.label == 0) & c.company).sum()), "late_recorded_cash_endpoints": int(c.late.sum())}
    jobs = []
    for k, (name, h, f, mode, sign, pool) in enumerate(SCENARIOS):
        if mode == "adversarial":
            jobs.append((name, h, f, mode, sign, pool, SEED + 1000 * k, 1))
        else:
            jobs += [(name, h, f, mode, sign, pool, SEED + 1000 * k + j, DRAWS // CHUNKS) for j in range(CHUNKS)]
    with ProcessPoolExecutor(8) as ex:
        outs = list(ex.map(scenario_draws, jobs))
    res = {}
    for name, o in outs:
        res.setdefault(name, []).extend(o)
    sjobs = [(k, SEED + 50000 + int(1000 * k) + j, SWEEP_DRAWS // CHUNKS) for k in KAPPAS for j in range(CHUNKS)]
    with ProcessPoolExecutor(8) as ex:
        souts = list(ex.map(sweep_draws, sjobs))
    sw = {}
    for k, o in souts:
        sw.setdefault(k, []).extend(o)
    sweep = [{"kappa": k, "full_mean": float(np.mean([x[0] for x in sw[k]])), "no_related_mean": float(np.mean([x[1] for x in sw[k]])),
              "recoded_effect_z": float(np.mean([x[2] for x in sw[k]]))} for k in KAPPAS]
    zs = [r["recoded_effect_z"] for r in sweep]
    breakdown = {"full_zero_at_effect_z": crossing(zs, [r["full_mean"] for r in sweep]),
                 "no_related_zero_at_effect_z": crossing(zs, [r["no_related_mean"] for r in sweep]),
                 "h": SWEEP_H, "f": SWEEP_F, "draws_per_kappa": SWEEP_DRAWS}
    # late or early recording: deterministic
    late = c[c.late]
    full, nr, cf, fc = fit_pair(apply(d, late), G)
    res["late_recording|all"] = [(full, nr, cf, fc, len(late))]
    pct = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    sim = {}
    for name, v in res.items():
        a = np.array(v, float)
        full, nr = a[:, 0], a[:, 1]
        sim[name] = {"draws": len(a), "recoded": float(a[:, 4].mean()), "cf_pairs": float(a[:, 2].mean()), "fc_pairs": float(a[:, 3].mean()),
                     "full_mean": float(full.mean()), "full_range": pct(full), "no_related_mean": float(nr.mean()), "no_related_range": pct(nr),
                     "share_removed_mean": float(((full - nr) / full).mean()), "share_removed_range": pct((full - nr) / full)}
    out = {"seed": SEED, "draws": DRAWS, "baseline": {"full": b_full, "no_related": b_nr, "pairs": len(d), "cf": b_cf, "fc": b_fc,
                                                      "reviewed_fixed": int(d.reviewed.sum())},
           "counts": counts, "scenarios": sim, "sweep": sweep, "breakdown": breakdown, "joint_table": joint_table(), "note": __doc__}
    (ROOT / "results/misclassification_checks.json").write_text(json.dumps(out, indent=1) + "\n")
    write_outputs(out)
    for k, s in sim.items():
        print(f"{k:34s} recoded {s['recoded']:6.0f} arms {s['cf_pairs']:6.0f}/{s['fc_pairs']:5.0f}  full {s['full_mean']:6.2f} "
              f"[{s['full_range'][0]:.2f}, {s['full_range'][1]:.2f}]  no-rel {s['no_related_mean']:5.2f}  removed {100 * s['share_removed_mean']:.0f}%")
    for r in out["joint_table"]["rows"]:
        print(f"{r['step']:28s} {r['pairs']:5d} {r['estimate']:6.2f} [{r['ci'][0]:.2f}, {r['ci'][1]:.2f}]  d-pub {r['change_from_published']:+.2f} "
              f"[{r['change_from_published_ci'][0]:+.2f}, {r['change_from_published_ci'][1]:+.2f}]  d-prev {r['change_from_previous']:+.2f}")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
