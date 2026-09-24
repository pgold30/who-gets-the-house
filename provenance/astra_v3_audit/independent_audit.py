"""Independent audit of v3 surname screen and joint financing regression.

Reads preserved raw inputs only. No imports from the paper's Python modules.
"""
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsqr

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "FINANCING_V3_0" / "replication"
ENTITY_WORDS = re.compile(
    r"\b(LLC|L\.L\.C|INC|CORP|CORPORATION|COMPANY|CO\.|BANK|TRUST|TRUSTEE|TRUSTEES|ESTATE|EXECUTOR|EXECUTRIX|ADMINISTRATOR|"
    r"ASSOCIATION|FUND|PARTNERS|LP|L\.P|HOLDINGS|REALTY|GROUP|MORTGAGE|FEDERAL|SECRETARY|CITY OF|MANAGEMENT|"
    r"PROPERTIES|DEVELOPMENT|CAPITAL|ASSOC|N\.A|FSB|SERVICING|REFEREE)\b"
)


def given_surname(name):
    value = name.strip().upper()
    if "," not in value or ENTITY_WORDS.search(value):
        return ""
    family = value.partition(",")[0].strip()
    return family if len(family) > 1 else ""


def surname_screen(parties, deeds):
    names = defaultdict(lambda: {"1": set(), "2": set()})
    for item in parties:
        family = given_surname(item.get("name", ""))
        role = item.get("party_type")
        if family and role in ("1", "2"):
            names[item["document_id"]][role].add(family)
    frequency = Counter(f for roles in names.values() for role in ("1", "2") for f in roles[role])
    common = {s for s, _ in frequency.most_common(40)}
    flag, strict = {}, {}
    for doc in deeds:
        roles = names.get(doc)
        overlap = roles["1"] & roles["2"] if roles else set()
        flag[doc] = bool(overlap)
        strict[doc] = bool(overlap - common)
    return flag, strict, sorted(common)


def make_design(frame):
    n = len(frame)
    label = {}
    rr, cc, vv = [], [], []
    for i, row in enumerate(frame.itertuples(index=False)):
        for side, sign in (("a", -1), ("z", 1)):
            day = pd.Timestamp(getattr(row, "date_" + side))
            quarter = (day.year - 2016) * 4 + (day.month - 1) // 3
            keys = []
            if quarter:
                keys.append(("quarter", row.borough, quarter))
            if day.year != 2016:
                keys.append(("zip_year", row.zipcode, day.year))
            for key in keys:
                j = label.setdefault(key, len(label))
                rr.append(i); cc.append(j); vv.append(sign)
    fe = sparse.coo_matrix((vv, (rr, cc)), shape=(n, len(label))).tocsr()
    extra = np.column_stack([
        frame[f"{role}_{group}_z"].to_numpy(dtype=float) - frame[f"{role}_{group}_a"].to_numpy(dtype=float)
        for role in ("buyer", "seller") for group in ("entity", "trust", "unknown")
    ])
    return sparse.hstack((fe, sparse.csr_matrix(extra)), format="csr")


def weighted_quantile(x, weights, p):
    order = np.argsort(x)
    x, weights = x[order], weights[order]
    plotting = (np.cumsum(weights) - weights / 2) / weights.sum()
    return np.interp(p, plotting, x)


def fit(design, treatments, outcome, weights, return_residual=False):
    active = weights > 0
    lhs = sparse.hstack((design[active], sparse.csr_matrix(treatments[active])), format="csr")
    root = np.sqrt(weights[active])
    lhs = lhs.multiply(root[:, None]).tocsr()
    colnorm = np.sqrt(np.asarray(lhs.power(2).sum(axis=0)).ravel())
    live = colnorm > 1e-12
    scaled = lhs[:, live].multiply(1 / colnorm[live]).tocsr()
    solution = lsqr(scaled, outcome[active] * root, atol=2e-11, btol=2e-11, iter_lim=10000)
    if solution[1] not in (0, 1, 2, 4, 5):
        raise RuntimeError(f"least squares did not converge: {solution[1:3]}")
    coef = np.zeros(lhs.shape[1]); coef[live] = solution[0] / colnorm[live]
    target = coef[-treatments.shape[1]:]
    if return_residual:
        residual = outcome[active] - (sparse.hstack((design[active], sparse.csr_matrix(treatments[active])), format="csr") @ coef)
        return target, residual
    return target


def contrast(beta):
    return float((beta[0] - beta[1]) / 2)


def huber(design, treatments, outcome, base):
    _, residual = fit(design, treatments, outcome, base, True)
    active = base > 0
    w = base[active]
    for stage in range(2):
        middle = weighted_quantile(residual, w, .5)
        scale = weighted_quantile(np.abs(residual - middle), w, .5) / .6745
        prior = None
        for iteration in range(1000):
            reweight = np.minimum(1, 1.345 * scale / np.maximum(np.abs(residual), 1e-12))
            weights = base.copy(); weights[active] *= reweight
            beta, residual = fit(design, treatments, outcome, weights, True)
            if prior is not None and np.max(np.abs(beta - prior)) < 1e-7:
                break
            prior = beta
        else:
            raise RuntimeError("Huber did not converge")
    return contrast(beta)


def main():
    data = pd.read_csv(SOURCE / "data/house_pairs_enriched.csv.gz", dtype={"bbl": str, "borough": str, "zipcode": str, "deed_a": str, "deed_z": str})
    assert int(data.cluster.max()) + 1 == 8127
    data = data.loc[data.permit_free & ~data.lender_high & data.geo_linked].copy().reset_index(drop=True)
    assert len(data) == 6006
    parties = json.loads((SOURCE / "data/parties.json").read_text())
    deeds = set(data.deed_a.dropna()) | set(data.deed_z.dropna())
    flag, strict, common = surname_screen(parties, deeds)
    for side in ("a", "z"):
        data[f"related_{side}"] = data[f"deed_{side}"].map(flag).fillna(False)
        data[f"strict_{side}"] = data[f"deed_{side}"].map(strict).fillna(False)
    related = (data.related_a | data.related_z).to_numpy(bool)
    related_strict = (data.strict_a | data.strict_z).to_numpy(bool)
    fa, fz = data.financed_base_a.to_numpy(), data.financed_base_z.to_numpy()
    cf, fc = (fa == 0) & (fz == 1), (fa == 1) & (fz == 0)
    company = np.where(cf, data.buyer_entity_a.to_numpy(bool), np.where(fc, data.buyer_entity_z.to_numpy(bool), False))
    q = np.column_stack((cf, fc)).astype(float)
    qs = np.column_stack((cf & company, cf & ~company, fc & company, fc & ~company)).astype(float)
    design = make_design(data)
    y = data.y.to_numpy()
    cl = data.cluster.to_numpy()
    masks = {"all": np.ones(len(data), bool), "no_related": ~related, "no_related_strict": ~related_strict}
    def one(mask, tr, weights):
        ww = weights * mask
        active = ww > 0
        return fit(design[active], tr[active], y[active], ww[active])
    point = {}
    ones = np.ones(len(data))
    for key, mask in masks.items():
        point[key + "|ols"] = contrast(one(mask, q, ones))
    point["no_related|huber"] = huber(design[~related], q[~related], y[~related], ones[~related])
    for key in ("all", "no_related"):
        b = one(masks[key], qs, ones)
        point[key + "|company"] = float((b[0] - b[2]) / 2)
        point[key + "|other"] = float((b[1] - b[3]) / 2)
    # Fixed RNG stream: one multinomial over all 8,127 parcel clusters per draw.
    rng = np.random.default_rng(20260909)
    draws = []
    for rep in range(999):
        count = rng.multinomial(8127, np.full(8127, 1 / 8127))
        weights = count[cl].astype(float)
        record = {}
        for key, mask in masks.items():
            record[key + "|ols"] = contrast(one(mask, q, weights))
        for key in ("all", "no_related"):
            b = one(masks[key], qs, weights)
            record[key + "|company"] = float((b[0] - b[2]) / 2)
            record[key + "|other"] = float((b[1] - b[3]) / 2)
        draws.append(record)
        if (rep + 1) % 100 == 0:
            print(f"completed {rep + 1}/999 draws", flush=True)
    result = pd.DataFrame(draws)
    endpoint = pd.concat([
        pd.DataFrame({"cash": data[f"financed_base_{side}"].eq(0), "related": data[f"related_{side}"]})
        for side in ("a", "z")
    ], ignore_index=True)
    summary = {
        "sample_pairs": len(data), "related_pairs": int(related.sum()), "strict_pairs": int(related_strict.sum()),
        "related_cash_endpoints": int((endpoint.cash & endpoint.related).sum()),
        "cash_endpoints": int(endpoint.cash.sum()),
        "related_financed_endpoints": int((~endpoint.cash & endpoint.related).sum()),
        "financed_endpoints": int((~endpoint.cash).sum()),
        "common_surnames": common,
        "point": point,
        "ci": {col: np.percentile(result[col], [2.5, 97.5]).tolist() for col in result.columns},
        "bootstrap": {"draws": 999, "seed": 20260909, "clusters": 8127},
    }
    (HERE / "independent_results.json").write_text(json.dumps(summary, indent=2) + "\n")
    data[["bbl", "deed_a", "deed_z", "related_a", "related_z", "strict_a", "strict_z"]].to_csv(HERE / "independent_flags.csv", index=False)
    print(json.dumps({"counts": [summary["related_pairs"], summary["strict_pairs"]], "point": point, "ci": summary["ci"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
