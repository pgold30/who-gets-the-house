"""Shared-mailing-address screen and independent refit on the house sample."""
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from independent_audit import contrast, fit, given_surname, make_design

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "FINANCING_V3_0" / "replication"
SUFFIX = {"STREET": "ST", "AVENUE": "AVE", "ROAD": "RD", "BOULEVARD": "BLVD", "DRIVE": "DR", "PLACE": "PL", "LANE": "LN", "COURT": "CT", "TERRACE": "TER", "PARKWAY": "PKWY"}


def street_key(record):
    raw = (record.get("address_1") or "").upper().strip()
    if not raw or re.search(r"\b(?:P\.?O\.?\s*BOX|C/O|CARE OF|ATTN)\b", raw):
        return None
    raw = re.sub(r"\b(?:APT|APARTMENT|UNIT|SUITE|STE|FL|FLOOR|#)\b.*$", "", raw)
    tokens = re.findall(r"[A-Z0-9]+", raw)
    if len(tokens) < 2 or not re.search(r"\d", tokens[0]):
        return None
    tokens = [SUFFIX.get(t, t) for t in tokens]
    city = " ".join(re.findall(r"[A-Z0-9]+", (record.get("city") or "").upper()))
    postal = re.sub(r"\D", "", record.get("zip") or "")[:5]
    if not city or len(postal) != 5:
        return None
    return (" ".join(tokens), city, postal)


def main():
    frame = pd.read_csv(SRC / "data/house_pairs_enriched.csv.gz", dtype={"bbl": str, "borough": str, "zipcode": str, "deed_a": str, "deed_z": str})
    frame = frame.loc[frame.permit_free & ~frame.lender_high & frame.geo_linked].reset_index(drop=True)
    flags = pd.read_csv(HERE / "independent_flags.csv", dtype={"bbl": str, "deed_a": str, "deed_z": str})
    assert len(frame) == len(flags) and (frame.bbl == flags.bbl).all()
    parties = json.loads((HERE / "house_party_addresses.json").read_text())
    by_doc = defaultdict(lambda: {"1": set(), "2": set()})
    by_doc_person = defaultdict(lambda: {"1": set(), "2": set()})
    for item in parties:
        k = street_key(item)
        if k and item.get("party_type") in ("1", "2"):
            by_doc[item["document_id"]][item["party_type"]].add(k)
            if given_surname(item.get("name", "")):
                by_doc_person[item["document_id"]][item["party_type"]].add(k)
    shared = {doc: bool(roles["1"] & roles["2"]) for doc, roles in by_doc.items()}
    shared_person = {doc: bool(roles["1"] & roles["2"]) for doc, roles in by_doc_person.items()}
    for side in ("a", "z"):
        frame[f"address_{side}"] = frame[f"deed_{side}"].map(shared).fillna(False).astype(bool)
        frame[f"address_person_{side}"] = frame[f"deed_{side}"].map(shared_person).fillna(False).astype(bool)
    pair_shared = (frame.address_a | frame.address_z).to_numpy(bool)
    pair_shared_person = (frame.address_person_a | frame.address_person_z).to_numpy(bool)
    surname = (flags.related_a | flags.related_z).to_numpy(bool)
    combined = pair_shared | surname
    combined_person = pair_shared_person | surname
    fa, fz = frame.financed_base_a.to_numpy(), frame.financed_base_z.to_numpy()
    q = np.column_stack(((fa == 0) & (fz == 1), (fa == 1) & (fz == 0))).astype(float)
    X, y, cl = make_design(frame), frame.y.to_numpy(), frame.cluster.to_numpy()
    active = ~combined
    active_person = ~combined_person
    no_surname = ~surname
    def estimate(mask, weights):
        keep = mask & (weights > 0)
        return contrast(fit(X[keep], q[keep], y[keep], weights[keep]))
    ones = np.ones(len(frame))
    point = {"all": estimate(np.ones(len(frame), bool), ones), "no_surname": estimate(no_surname, ones), "no_surname_or_address": estimate(active, ones),
             "no_surname_or_person_address": estimate(active_person, ones)}
    rng = np.random.default_rng(20260909)
    draws = np.empty((999, 3))
    for i in range(999):
        w = rng.multinomial(8127, np.full(8127, 1 / 8127))[cl].astype(float)
        draws[i] = [estimate(no_surname, w), estimate(active, w), estimate(active_person, w)]
        if (i + 1) % 200 == 0:
            print(f"completed {i + 1}/999 draws", flush=True)
    counts = {
        "shared_address_pairs": int(pair_shared.sum()),
        "surname_pairs": int(surname.sum()),
        "combined_pairs": int(combined.sum()),
        "additional_address_only_pairs": int((pair_shared & ~surname).sum()),
        "shared_person_address_pairs": int(pair_shared_person.sum()),
        "additional_person_address_only_pairs": int((pair_shared_person & ~surname).sum()),
        "remaining_pairs": int(active.sum()),
        "remaining_person_address_pairs": int(active_person.sum()),
        "cash_endpoints_shared": int((frame.address_a & (fa == 0)).sum() + (frame.address_z & (fz == 0)).sum()),
        "financed_endpoints_shared": int((frame.address_a & (fa == 1)).sum() + (frame.address_z & (fz == 1)).sum()),
    }
    result = {"counts": counts, "point": point,
              "ci": {"no_surname": np.percentile(draws[:, 0], [2.5, 97.5]).tolist(), "no_surname_or_address": np.percentile(draws[:, 1], [2.5, 97.5]).tolist(),
                     "additional_change": np.percentile(draws[:, 1] - draws[:, 0], [2.5, 97.5]).tolist(),
                     "no_surname_or_person_address": np.percentile(draws[:, 2], [2.5, 97.5]).tolist(),
                     "additional_person_change": np.percentile(draws[:, 2] - draws[:, 0], [2.5, 97.5]).tolist()},
              "additional_change_point": point["no_surname_or_address"] - point["no_surname"],
              "additional_person_change_point": point["no_surname_or_person_address"] - point["no_surname"],
              "bootstrap": {"draws": 999, "seed": 20260909, "clusters": 8127},
              "normalization": "Uppercase address_1; remove punctuation and apartment/unit suffix; standardize common street suffixes; require identical street, city, and five-digit ZIP. Exclude PO boxes and care-of addresses. Flag any grantor/grantee pair regardless of name or entity type. This is shared mailing address, not proof of kinship."}
    (HERE / "address_results.json").write_text(json.dumps(result, indent=2) + "\n")
    pd.DataFrame({"bbl": frame.bbl, "deed_a": frame.deed_a, "deed_z": frame.deed_z, "shared_address_a": frame.address_a, "shared_address_z": frame.address_z,
                  "person_shared_address_a": frame.address_person_a, "person_shared_address_z": frame.address_person_z,
                  "surname_pair": surname, "combined_pair": combined, "combined_person_pair": combined_person}).to_csv(HERE / "address_flags.csv", index=False)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
