"""Score the house financing labels against the cross-AI instrument review.

The original protocol (audit/FOCUSED_REVIEW_PROTOCOL.md) called for two human
readers; this version uses two independent AI readings instead. ChatGPT read the
deed and candidate mortgages for all 106 endpoints of the frozen queue
(audit/cross_ai_review/house_readings_chatgpt.csv). Claude checked each reading
against ACRIS open data (opendata_check_claude.csv) and returned inconsistent
readings for a second look; the corrections are already in the readings file.
The readings were locked before the analyst key was opened.

An endpoint is decisive only when its reading is PURCHASE_MORTGAGE_SUPPORTED
with the mortgage, borrower, collateral, purchase purpose and pages documented
(financed), or DOCUMENTED_UNFINANCED (cash). A pair is an error if either
endpoint decisively contradicts its label, correct if both agree, and unknown
otherwise. The script also refits the headline house model without the pairs
that carry a documented error.

Writes results/cross_ai_review.json and paper/generated/review_numbers.tex.
"""
import csv, hashlib, json, math, sys
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "audit"
REV = AUD / "cross_ai_review"
KEY_SHA256 = "c57075d1462c944cd784f1b7ad44b2c2c71c9708bc7011e73ad9de84723c0ca0"
FIN = {"PURCHASE_MORTGAGE_SUPPORTED", "DOCUMENTED_UNFINANCED", "OTHER_FINANCING_OR_CONFLICT", "INSUFFICIENT_EVIDENCE"}
DIS = {"FORECLOSURE_CONVEYANCE", "DOCUMENTED_LENDER_RESALE", "OTHER_SPECIAL_TRANSFER", "NO_AFFIRMATIVE_DISTRESS_EVIDENCE", "UNRESOLVED"}
EDITABLE = {"reviewed_financing", "purchase_mortgage_document_id", "borrower_buyer_match", "collateral_match",
            "purchase_vs_refinance", "mortgage_pages"}
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "inputs/3_section4.9"))


def read(p):
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))


def wilson(x, n, alpha=0.05):
    z = NormalDist().inv_cdf(1 - alpha / 2); p = x / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def readings(overrides=None):
    sheet = {(r["case_id"], r["endpoint"]): dict(r) for r in read(REV / "house_readings_chatgpt.csv")}
    blind = {(r["case_id"], r["endpoint"]): r for r in read(AUD / "focused_blinded_house_review.csv")}
    if set(sheet) != set(blind) or len(blind) != 106:
        raise ValueError("readings and frozen queue differ")
    for k, r in sheet.items():
        if r["bbl"] != blind[k]["bbl"] or r["sale_date"] != blind[k]["sale_date"]:
            raise ValueError(f"parcel or date changed for {k}")
        if r["reviewed_financing"] not in FIN or r["reviewed_distress"] not in DIS:
            raise ValueError(f"invalid code for {k}")
    for o in (read(overrides) if overrides else []):
        k = (o["case_id"], o["endpoint"])
        if k not in sheet or o["field"] not in EDITABLE or not o.get("source") or not o.get("reason"):
            raise ValueError(f"bad override: {o}")
        sheet[k][o["field"]] = o["value"]
    return sheet, blind


def decisive(r):
    if r["reviewed_financing"] == "PURCHASE_MORTGAGE_SUPPORTED":
        ok = (r["purchase_mortgage_document_id"] and r["borrower_buyer_match"] == "Y" and r["collateral_match"] == "Y"
              and r["purchase_vs_refinance"] == "PURCHASE" and r["mortgage_pages"])
        return 1 if ok else None
    return 0 if r["reviewed_financing"] == "DOCUMENTED_UNFINANCED" else None


def score(sheet, keyrows):
    status, errors = {}, []
    ep = {"financed_confirmed": 0, "financed_total": 0, "cash_with_mortgage": 0, "cash_total": 0}
    for k in keyrows:
        st = []
        for e in "az":
            d, orig = decisive(sheet[(k["case_id"], e)]), int(k["flag_" + e])
            ep["financed_total" if orig else "cash_total"] += 1
            if d == 1:
                ep["financed_confirmed" if orig else "cash_with_mortgage"] += 1
            if d is None:
                st.append("unknown")
            else:
                st.append("correct" if d == orig else "error")
                if d != orig:
                    errors.append(k["case_id"] + "-" + e)
        status[k["case_id"]] = "error" if "error" in st else ("correct" if st == ["correct", "correct"] else "unknown")
    arms = {}
    for arm in ("cash_to_financed", "financed_to_cash"):
        rows = [r for r in keyrows if r["sample_kind"] == "probability_sample" and r["switch_group"] == arm]
        assert len(rows) == 20 and len({r["pair_selection_probability"] for r in rows}) == 1
        c = {s: sum(status[r["case_id"]] == s for r in rows) for s in ("error", "correct", "unknown")}
        arms[arm] = {"population_pairs": round(20 / float(rows[0]["pair_selection_probability"])), "counts": c}
    tot = sum(a["population_pairs"] for a in arms.values())
    bounds = [sum(a["population_pairs"] * a["counts"]["error"] for a in arms.values()) / 20 / tot,
              sum(a["population_pairs"] * (a["counts"]["error"] + a["counts"]["unknown"]) for a in arms.values()) / 20 / tot]
    ep["cash_with_mortgage_95ci"] = wilson(ep["cash_with_mortgage"], ep["cash_total"])
    return {"endpoints": ep, "label_errors": errors, "error_pairs": sorted({e[:4] for e in errors}),
            "probability_arms": arms, "pair_error_bounds": bounds,
            "targeted": {s: sum(status[r["case_id"]] == s for r in keyrows if r["sample_kind"] != "probability_sample")
                         for s in ("error", "correct", "unknown")}}


def headline(blind, drop_cases):
    import analyze_repeat_sales as ars
    df = pd.read_csv(ROOT / "data/house_pairs_enriched.csv.gz", dtype={"bbl": str, "zipcode": str, "cd": str})
    for c in ("date_a", "date_z"):
        df[c] = pd.to_datetime(df[c]).dt.date
    df["zipcode"] = df["zipcode"].fillna("").str.replace(r"\.0$", "", regex=True)
    for c in ("permit_free", "lender_high", "geo_linked"):
        df[c] = df[c].astype(str).str.lower().isin(["true", "1"])
    G = df.cluster.max() + 1
    mask = df.permit_free & ~df.lender_high & df.geo_linked
    drop = {(blind[(c, "a")]["bbl"], blind[(c, "a")]["sale_date"], blind[(c, "z")]["sale_date"]) for c in drop_cases}
    keep = np.array([k not in drop for k in zip(df.bbl, df.date_a.astype(str), df.date_z.astype(str))])
    out = {}
    for name, m in (("published", mask), ("corrected", mask & keep)):
        sub = df.loc[m].copy()
        r, *_ = ars.estimate(sub, ars.design(sub, "zipcode", True), G)
        out[name] = {"pairs": int(r["pairs"]), "logpoints": 100 * r["pi_joint"], "ci": [100 * x for x in r["ci_joint"]]}
    assert abs(out["published"]["logpoints"] - 9.25) < 0.006 and out["published"]["pairs"] == 6006
    assert out["published"]["pairs"] - out["corrected"]["pairs"] == len(drop_cases)
    return out


def main():
    key_path = AUD / "focused_review_ANALYST_KEY.csv"
    if hashlib.sha256(key_path.read_bytes()).hexdigest() != KEY_SHA256:
        sys.exit("analyst key hash mismatch")
    keyrows = read(key_path)
    sheet, blind = readings()
    main_r = score(sheet, keyrows)
    sens = score(readings(REV / "sensitivity_timing.csv")[0], keyrows)
    main_r["headline"] = headline(blind, main_r["error_pairs"])
    sens["headline"] = headline(blind, sens["error_pairs"])
    res = {"key_sha256": KEY_SHA256, "main": main_r, "sensitivity_timing": sens,
           "note": "Analytic parcel-clustered intervals for both the published and the corrected fit."}
    (ROOT / "results/cross_ai_review.json").write_text(json.dumps(res, indent=2) + "\n")
    e, h, s = main_r["endpoints"], main_r["headline"], sens
    ci = lambda v: f"[{v[0]:.2f}, {v[1]:.2f}]"
    macros = {
        "ReviewFinConfirmed": e["financed_confirmed"], "ReviewFinTotal": e["financed_total"],
        "ReviewCashMtg": e["cash_with_mortgage"], "ReviewCashTotal": e["cash_total"],
        "ReviewCashShare": f"{100 * e['cash_with_mortgage'] / e['cash_total']:.0f}",
        "ReviewCashCI": f"{100 * e['cash_with_mortgage_95ci'][0]:.0f}--{100 * e['cash_with_mortgage_95ci'][1]:.0f}",
        "ReviewErrPairs": len(main_r["error_pairs"]),
        "ReviewArmErrors": main_r["probability_arms"]["financed_to_cash"]["counts"]["error"],
        "ReviewPairLow": f"{100 * main_r['pair_error_bounds'][0]:.1f}",
        "ReviewPairHigh": f"{100 * main_r['pair_error_bounds'][1]:.0f}",
        "ReviewPublishedAnalytic": f"{h['published']['logpoints']:.2f}", "ReviewPublishedAnalyticCI": ci(h["published"]["ci"]),
        "ReviewCorrected": f"{h['corrected']['logpoints']:.2f}", "ReviewCorrectedCI": ci(h["corrected"]["ci"]),
        "ReviewSensCashMtg": s["endpoints"]["cash_with_mortgage"], "ReviewSensFinConfirmed": s["endpoints"]["financed_confirmed"],
        "ReviewSensCorrected": f"{s['headline']['corrected']['logpoints']:.2f}",
    }
    (ROOT / "paper/generated/review_numbers.tex").write_text(
        "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items()))
    print(json.dumps(macros, indent=1))


if __name__ == "__main__":
    main()
