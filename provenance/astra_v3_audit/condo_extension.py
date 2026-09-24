"""Condominium surname screen and common borough-quarter contrast."""
import json
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

from independent_audit import contrast, fit, given_surname

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "FINANCING_V3_0" / "replication"
CACHE = HERE / "condo_party_pages"


def get(params):
    url = "https://data.cityofnewyork.us/resource/636b-3b5g.json?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "WhoGetsTheHouse-independent-audit/1.0"}), timeout=90) as response:
                return json.load(response)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(min(30, 2 ** attempt))


def page(index, ids):
    dest = CACHE / f"page_{index:04d}.json"
    if dest.exists():
        saved = json.loads(dest.read_text())
        assert saved["ids"] == ids and saved["count"] == len(saved["rows"])
        return saved
    where = "document_id in(" + ",".join("'" + s + "'" for s in ids) + ") AND party_type in('1','2')"
    count = int(get({"$select": "count(1)", "$where": where})[0]["count_1"])
    rows = get({"$select": "document_id,party_type,name", "$where": where, "$order": "document_id", "$limit": 50000})
    assert count == len(rows), (index, count, len(rows))
    saved = {"ids": ids, "count": count, "rows": rows}
    dest.write_text(json.dumps(saved))
    return saved


def quarter_design(frame):
    label, rr, cc, vv = {}, [], [], []
    for i, r in enumerate(frame.itertuples(index=False)):
        for side, sign in (("a", -1), ("z", 1)):
            date = pd.Timestamp(getattr(r, "date_" + side))
            q = (date.year - 2016) * 4 + (date.month - 1) // 3
            if q:
                j = label.setdefault((r.borough, q), len(label))
                rr.append(i); cc.append(j); vv.append(sign)
    return sparse.coo_matrix((vv, (rr, cc)), shape=(len(frame), len(label))).tocsr()


def main():
    CACHE.mkdir(exist_ok=True)
    frame = pd.read_csv(HERE / "condo_pairs_with_deeds.csv", dtype={"bbl": str, "borough": str, "deed_a": str, "deed_z": str})
    ids = sorted((set(frame.deed_a.dropna()) | set(frame.deed_z.dropna())) - {""})
    pages = [ids[i:i + 100] for i in range(0, len(ids), 100)]
    collected = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(page, i, batch): i for i, batch in enumerate(pages)}
        for future in as_completed(futures):
            collected.append((futures[future], future.result()))
            if len(collected) % 20 == 0:
                print(f"party: verified {len(collected)}/{len(pages)} pages", flush=True)
    collected.sort()
    parties = [r for _, x in collected for r in x["rows"]]
    (HERE / "condo_parties.json").write_text(json.dumps(parties))
    roles = defaultdict(lambda: {"1": set(), "2": set()})
    for item in parties:
        surname = given_surname(item.get("name", ""))
        if surname and item.get("party_type") in ("1", "2"):
            roles[item["document_id"]][item["party_type"]].add(surname)
    frequency = Counter(s for sides in roles.values() for role in ("1", "2") for s in sides[role])
    common = {s for s, _ in frequency.most_common(40)}
    flag = {doc: bool(sides["1"] & sides["2"]) for doc, sides in roles.items()}
    strict = {doc: bool((sides["1"] & sides["2"]) - common) for doc, sides in roles.items()}
    for side in ("a", "z"):
        frame["related_" + side] = frame["deed_" + side].map(flag).fillna(False).astype(bool)
        frame["strict_" + side] = frame["deed_" + side].map(strict).fillna(False).astype(bool)
    related = (frame.related_a | frame.related_z).to_numpy(bool)
    related_strict = (frame.strict_a | frame.strict_z).to_numpy(bool)
    X = quarter_design(frame)
    y = frame.y.to_numpy(float)
    fa, fz = frame.financed_base_a.to_numpy(), frame.financed_base_z.to_numpy()
    q = np.column_stack(((fa == 0) & (fz == 1), (fa == 1) & (fz == 0))).astype(float)
    cl = frame.cluster.to_numpy(int)
    G = int(cl.max()) + 1
    def estimate(mask, weights):
        use = mask & (weights > 0)
        return contrast(fit(X[use], q[use], y[use], weights[use]))
    ones = np.ones(len(frame))
    allmask, screen, screen_strict = np.ones(len(frame), bool), ~related, ~related_strict
    point = {"all": estimate(allmask, ones), "no_surname": estimate(screen, ones), "no_surname_strict": estimate(screen_strict, ones)}
    rng = np.random.default_rng(20260909)
    draws = np.empty((999, 3))
    for i in range(999):
        w = rng.multinomial(G, np.full(G, 1/G))[cl].astype(float)
        draws[i] = (estimate(allmask, w), estimate(screen, w), estimate(screen_strict, w))
        if (i+1) % 200 == 0:
            print(f"bootstrap {i+1}/999", flush=True)
    party_docs = {r["document_id"] for r in parties}
    result = {"pairs": len(frame), "clusters": G, "matched_deed_endpoints": int(frame.deed_a.notna().sum() + frame.deed_z.notna().sum()),
              "party_covered_endpoints": int(frame.deed_a.isin(party_docs).sum() + frame.deed_z.isin(party_docs).sum()),
              "party_rows": len(parties), "party_pages": len(pages), "related_pairs": int(related.sum()),
              "related_pairs_strict": int(related_strict.sum()), "remaining_pairs": int(screen.sum()), "point": point,
              "ci": {"all": np.percentile(draws[:, 0], [2.5, 97.5]).tolist(), "no_surname": np.percentile(draws[:, 1], [2.5, 97.5]).tolist(),
                     "change": np.percentile(draws[:, 1]-draws[:, 0], [2.5, 97.5]).tolist(),
                     "no_surname_strict": np.percentile(draws[:, 2], [2.5, 97.5]).tolist()},
              "change_point": point["no_surname"]-point["all"], "seed": 20260909, "draws": 999}
    (HERE / "condo_results.json").write_text(json.dumps(result, indent=2) + "\n")
    frame[["bbl", "deed_a", "deed_z", "related_a", "related_z", "strict_a", "strict_z"]].to_csv(HERE / "condo_flags.csv", index=False)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
