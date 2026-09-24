"""Same-surname screen across property types, and a shared-address sensitivity (v3.1).

Extends related_party.py in two directions, from preserved extracts only:

1. Condominiums. Deeds for condominium endpoints and their parties were
   retrieved from ACRIS (legals 8h5j-fqxa, master bnx9-e6tj, parties 636b-3b5g)
   with every indexed page checked against count(1)
   (data/condo_fetch_manifest.json). The same surname rule is applied, and the
   common borough-quarter house and condominium contrasts of Table 4 are
   re-estimated without flagged pairs.
2. Shared address. Grantor and grantee mailing addresses on each house endpoint
   deed (data/house_party_addresses.json.gz, data/address_fetch_manifest.json)
   are normalized to street, city and five-digit ZIP. Pairs with a deed whose
   grantor and grantee share one are excluded in addition to same-surname
   pairs. A shared mailing address is a proxy for co-location or a common
   mailing agent, not proof of kinship.

The retrieval and first estimates were made independently in the audit whose
scripts are preserved in provenance/astra_v3_audit/. This script recomputes them
with the package's own design and the paper's bootstrap draws (seed 20260909).
"""
import gzip, json, re
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from analyze_repeat_sales import DATA, OUT, REP, SEED, design
from legacy_estimator import load_panel, build
from robust_estimators import wls, switches, multinomials
from related_party import surname, N_COMMON

SUFFIX = {'STREET': 'ST', 'AVENUE': 'AVE', 'ROAD': 'RD', 'BOULEVARD': 'BLVD', 'DRIVE': 'DR', 'PLACE': 'PL',
          'LANE': 'LN', 'COURT': 'CT', 'TERRACE': 'TER', 'PARKWAY': 'PKWY'}


def street_key(r):
    raw = (r.get('address_1') or '').upper().strip()
    if not raw or re.search(r'\b(?:P\.?O\.?\s*BOX|C/O|CARE OF|ATTN)\b', raw):
        return None
    raw = re.sub(r'\b(?:APT|APARTMENT|UNIT|SUITE|STE|FL|FLOOR|#)\b.*$', '', raw)
    tokens = re.findall(r'[A-Z0-9]+', raw)
    if len(tokens) < 2 or not re.search(r'\d', tokens[0]):
        return None
    tokens = [SUFFIX.get(t, t) for t in tokens]
    city = ' '.join(re.findall(r'[A-Z0-9]+', (r.get('city') or '').upper()))
    postal = re.sub(r'\D', '', r.get('zip') or '')[:5]
    if not city or len(postal) != 5:
        return None
    return (' '.join(tokens), city, postal)


def surname_flags(parties):
    by_doc = defaultdict(lambda: {'1': set(), '2': set()})
    for r in parties:
        s = surname(r['name'].upper().strip())
        if s and r['party_type'] in ('1', '2'):
            by_doc[r['document_id']][r['party_type']].add(s)
    common = {s for s, _ in Counter(s for v in by_doc.values() for t in '12' for s in v[t]).most_common(N_COMMON)}
    flag = {d: bool(v['1'] & v['2']) for d, v in by_doc.items()}
    strict = {d: bool((v['1'] - common) & (v['2'] - common)) for d, v in by_doc.items()}
    return flag, strict, {r['document_id'] for r in parties}


def contrast(X, Q, y, w, m):
    m = m & (w > 0)
    b, _ = wls(X[m], Q[m], y[m], w[m])
    return .5 * (b[0] - b[1])


def pairs_from_panel(typ):
    """Rebuild the Table 4 pairs exactly as robust_estimators.py does."""
    rows, _ = load_panel(REP / '2_reproduce')
    recs = []
    for a, z, da, dz in build([r for r in rows if r['src'] == typ], int(36 * 30.44)):
        recs.append({'bbl': a['bbl'], 'borough': a['borough'], 'date_a': da, 'date_z': dz,
                     'y': np.log(float(z['price']) / float(a['price'])),
                     'financed_base_a': int(a['financed_base']), 'financed_base_z': int(z['financed_base'])})
    df = pd.DataFrame(recs); _, df['cluster'] = np.unique(df.bbl, return_inverse=True)
    return df


def attach_deeds(df, deeds):
    deeds = deeds.copy()
    for s in 'az': deeds['date_' + s] = pd.to_datetime(deeds['date_' + s]).dt.date
    m = df.merge(deeds[['bbl', 'date_a', 'date_z', 'deed_a', 'deed_z']], on=['bbl', 'date_a', 'date_z'], how='left', validate='one_to_one')
    assert len(m) == len(df) and (m.bbl.to_numpy() == df.bbl.to_numpy()).all()
    return m


def bootstrap(fns, cl, G):
    draws = []
    for w in multinomials(G, SEED):
        ww = w[cl].astype(float); draws.append([f(ww) for f in fns])
    return np.array(draws)


def main():
    res = {}
    pct = lambda v: np.percentile(v, [2.5, 97.5]).tolist()

    # 1. Common borough-quarter design, houses and condominiums
    hp = pd.read_csv(DATA / 'house_pairs_enriched.csv.gz', dtype={'bbl': str, 'borough': str, 'deed_a': str, 'deed_z': str})
    hflag, hstrict, hdocs = surname_flags(json.loads((DATA / 'parties.json').read_text()))
    cp = pd.read_csv(DATA / 'condo_pairs_with_deeds.csv.gz', dtype={'bbl': str, 'borough': str, 'deed_a': str, 'deed_z': str})
    cparties = json.loads(gzip.open(DATA / 'condo_parties.json.gz').read())
    cflag, cstrict, cdocs = surname_flags(cparties)
    for typ, deeds, flag, strict, docs in [('house', hp, hflag, hstrict, hdocs), ('condo', cp, cflag, cstrict, cdocs)]:
        df = attach_deeds(pairs_from_panel(typ), deeds)
        if typ == 'condo':  # the preserved condo extract must describe the same pairs
            chk = cp.set_index(['bbl', 'date_a', 'date_z'])
            assert len(chk) == len(df) and np.allclose(np.sort(chk.y.to_numpy()), np.sort(df.y.to_numpy()))
        rel = np.zeros(len(df), bool); rel_s = np.zeros(len(df), bool); cover = 0; matched = 0
        for s in 'az':
            ids = df['deed_' + s]
            matched += int(ids.notna().sum()); cover += int(ids.isin(docs).sum())
            rel |= np.array([bool(flag.get(x, False)) for x in ids])
            rel_s |= np.array([bool(strict.get(x, False)) for x in ids])
        X = design(df); Q = switches(df); y = df.y.to_numpy(); G = int(df.cluster.max() + 1); cl = df.cluster.to_numpy()
        one = np.ones(len(df)); allm = np.ones(len(df), bool)
        fns = [lambda w: contrast(X, Q, y, w, allm), lambda w: contrast(X, Q, y, w, ~rel), lambda w: contrast(X, Q, y, w, ~rel_s)]
        point = [f(one) for f in fns]
        D = bootstrap(fns, cl, G)
        res[typ + '_borough_quarter'] = {
            'pairs': len(df), 'clusters': G, 'endpoints': 2 * len(df), 'endpoints_with_deed': matched, 'endpoints_with_party_records': cover,
            'flagged_pairs': int(rel.sum()), 'flagged_pairs_strict': int(rel_s.sum()),
            'point': {'all': point[0], 'no_related': point[1], 'no_related_strict': point[2]},
            'ci': {'all': pct(D[:, 0]), 'no_related': pct(D[:, 1]), 'no_related_strict': pct(D[:, 2])},
            'change': {'estimate': point[1] - point[0], 'ci': pct(D[:, 1] - D[:, 0])}}
        print(typ, {k: round(100 * v, 2) for k, v in res[typ + '_borough_quarter']['point'].items()}, flush=True)
    H, C = res['house_borough_quarter'], res['condo_borough_quarter']
    assert abs(100 * H['point']['all'] - 11.42) < 0.005 and abs(100 * C['point']['all'] - 0.77) < 0.005
    rob = json.loads((OUT / 'robust_estimates.json').read_text())
    assert np.allclose(C['ci']['all'], rob['condo_borough_quarter']['ci']['ols'], atol=1e-7)
    assert np.allclose(H['ci']['all'], rob['house_borough_quarter']['ci']['ols'], atol=1e-7)
    manifest = json.loads((DATA / 'condo_fetch_manifest.json').read_text())
    C['deed_linkage'] = {k: manifest[k] for k in ['endpoint_deeds_matched', 'total_endpoints', 'ambiguous_endpoints', 'method']}

    # 2. Shared-address sensitivity in the headline house specification
    d = hp[hp.permit_free & ~hp.lender_high & hp.geo_linked].copy().reset_index(drop=True)
    for s in 'az': d['date_' + s] = pd.to_datetime(d['date_' + s]).dt.date
    assert len(d) == 6006
    addr = defaultdict(lambda: {'1': set(), '2': set()}); addr_p = defaultdict(lambda: {'1': set(), '2': set()})
    for r in json.loads(gzip.open(DATA / 'house_party_addresses.json.gz').read()):
        k = street_key(r)
        if k and r['party_type'] in ('1', '2'):
            addr[r['document_id']][r['party_type']].add(k)
            if surname(r['name'].upper().strip()):
                addr_p[r['document_id']][r['party_type']].add(k)
    shared = {k: bool(v['1'] & v['2']) for k, v in addr.items()}; shared_p = {k: bool(v['1'] & v['2']) for k, v in addr_p.items()}
    fl = lambda ids, mp: np.array([bool(mp.get(x, False)) for x in ids])
    sur = fl(d.deed_a, hflag) | fl(d.deed_z, hflag)
    sh = fl(d.deed_a, shared) | fl(d.deed_z, shared); shp = fl(d.deed_a, shared_p) | fl(d.deed_z, shared_p)
    X = design(d, 'zipcode', True); Q = switches(d); y = d.y.to_numpy(); cl = d.cluster.to_numpy(); one = np.ones(len(d))
    fns = [lambda w: contrast(X, Q, y, w, ~sur), lambda w: contrast(X, Q, y, w, ~(sur | sh)), lambda w: contrast(X, Q, y, w, ~(sur | shp))]
    point = [f(one) for f in fns]
    D = bootstrap(fns, cl, 8127)
    fa, fz = d.financed_base_a.to_numpy(), d.financed_base_z.to_numpy()
    sh_a, sh_z = fl(d.deed_a, shared), fl(d.deed_z, shared)
    res['house_shared_address'] = {
        'pairs': len(d), 'surname_pairs': int(sur.sum()), 'shared_address_pairs': int(sh.sum()),
        'additional_address_pairs': int((sh & ~sur).sum()), 'remaining_pairs': int((~(sur | sh)).sum()),
        'shared_person_address_pairs': int(shp.sum()), 'additional_person_address_pairs': int((shp & ~sur).sum()),
        'remaining_person_pairs': int((~(sur | shp)).sum()),
        'shared_share_of_endpoints': {'cash': float((sh_a[fa == 0].sum() + sh_z[fz == 0].sum()) / ((fa == 0).sum() + (fz == 0).sum())),
                                      'financed': float((sh_a[fa == 1].sum() + sh_z[fz == 1].sum()) / ((fa == 1).sum() + (fz == 1).sum()))},
        'point': {'no_surname': point[0], 'no_surname_or_address': point[1], 'no_surname_or_person_address': point[2]},
        'ci': {'no_surname': pct(D[:, 0]), 'no_surname_or_address': pct(D[:, 1]), 'no_surname_or_person_address': pct(D[:, 2])},
        'additional_change': {'estimate': point[1] - point[0], 'ci': pct(D[:, 1] - D[:, 0])},
        'additional_person_change': {'estimate': point[2] - point[0], 'ci': pct(D[:, 2] - D[:, 0])},
        'normalization': 'address_1 upper-cased; PO boxes and care-of addresses dropped; apartment/unit suffix removed; common street suffixes standardized; identical street, city and five-digit ZIP required.'}
    rp = json.loads((OUT / 'related_party.json').read_text())
    assert abs(point[0] - rp['point']['no_related|ols']) < 1e-9
    assert np.allclose(pct(D[:, 0]), rp['ci']['no_related|ols'], atol=1e-7)
    res['bootstrap'] = {'draws': 999, 'seed': SEED}
    (OUT / 'related_party_extensions.json').write_text(json.dumps(res, indent=2))
    write_outputs(res)


def write_outputs(res):
    H, C, A = res['house_borough_quarter'], res['condo_borough_quarter'], res['house_shared_address']
    f = lambda v: f'{100 * v:.2f}'
    ci = lambda c: '[{:.2f}, {:.2f}]'.format(100 * c[0], 100 * c[1])
    rows_a = [f"Houses & {H['pairs']:,} & {f(H['point']['all'])} {ci(H['ci']['all'])} & {H['flagged_pairs']:,} & {f(H['point']['no_related'])} {ci(H['ci']['no_related'])} & {f(H['change']['estimate'])} {ci(H['change']['ci'])} \\\\",
              f"Condominiums & {C['pairs']:,} & {f(C['point']['all'])} {ci(C['ci']['all'])} & {C['flagged_pairs']:,} & {f(C['point']['no_related'])} {ci(C['ci']['no_related'])} & {f(C['change']['estimate'])} {ci(C['change']['ci'])} \\\\"]
    rows_b = [f"Same-surname deeds & {A['pairs'] - A['surname_pairs']:,} & {f(A['point']['no_surname'])} {ci(A['ci']['no_surname'])} & \\multicolumn{{2}}{{l}}{{}} \\\\",
              f"\\quad or shared address & {A['remaining_pairs']:,} & {f(A['point']['no_surname_or_address'])} {ci(A['ci']['no_surname_or_address'])} & \\multicolumn{{2}}{{l}}{{{f(A['additional_change']['estimate'])} {ci(A['additional_change']['ci'])}}} \\\\",
              f"\\quad or shared address, persons & {A['remaining_person_pairs']:,} & {f(A['point']['no_surname_or_person_address'])} {ci(A['ci']['no_surname_or_person_address'])} & \\multicolumn{{2}}{{l}}{{{f(A['additional_person_change']['estimate'])} {ci(A['additional_person_change']['ci'])}}} \\\\"]
    tex = r'''\begin{table}[htbp]\centering\footnotesize\setlength{\tabcolsep}{2pt}
\caption{The same-surname screen across property types, and a shared-address sensitivity}\label{tab:relatedext}
\begin{tabular}{lrlrll}\toprule
\multicolumn{6}{l}{\textit{A. Common borough-quarter design (Table~\ref{tab:property})}}\\
 & Pairs & All pairs & Flagged & Unflagged pairs & Change \\
\midrule
''' + '\n'.join(rows_a) + r'''
\midrule
\multicolumn{6}{l}{\textit{B. Headline house specification: excluding pairs with}}\\
 & Pairs & Contrast & \multicolumn{2}{l}{Change vs.\ surname screen} & \\
\midrule
''' + '\n'.join(rows_b) + r'''
\bottomrule\end{tabular}
\notes{Log points; 95\% percentile intervals from the paper's 999 common parcel-bootstrap draws (seed 20260909), refitting all controls in each draw. Panel A: least squares under borough-quarter effects only, as in Table~\ref{tab:property}; the same-surname flag of Table~\ref{tab:related} is applied to deeds linked to each endpoint. Condominium deeds are linked for MATCHED of TOTAL endpoints (AMBIG ambiguous matches left unlinked). Panel B: headline specification of Table~\ref{tab:cumulative}. A shared address is a grantor and grantee on the same deed with the same normalized mailing street, city and ZIP code; it can reflect a common mailing agent or co-location and is not evidence of kinship. The natural-person variant counts only addresses of parties with personal names.}
\end{table}
'''
    tex = tex.replace('MATCHED', f"{C['deed_linkage']['endpoint_deeds_matched']:,}").replace('TOTAL', f"{C['deed_linkage']['total_endpoints']:,}").replace('AMBIG', str(C['deed_linkage']['ambiguous_endpoints']))
    gen = OUT.parent / 'paper/generated'
    (gen / 'related_ext.tex').write_text(tex)
    m = {'CondoFlagged': f"{C['flagged_pairs']:,}", 'CondoFlaggedStrict': f"{C['flagged_pairs_strict']:,}",
         'CondoNoRel': f(C['point']['no_related']), 'CondoNoRelCI': ci(C['ci']['no_related']),
         'CondoNoRelStrict': f(C['point']['no_related_strict']), 'CondoNoRelStrictCI': ci(C['ci']['no_related_strict']),
         'CondoRelChange': f(C['change']['estimate']), 'CondoRelChangeCI': ci(C['change']['ci']),
         'CondoBootCI': ci(C['ci']['all']),
         'CondoDeedEnds': f"{C['deed_linkage']['endpoint_deeds_matched']:,}", 'CondoEnds': f"{C['deed_linkage']['total_endpoints']:,}",
         'CondoAmbiguous': str(C['deed_linkage']['ambiguous_endpoints']),
         'HouseBQFlagged': f"{H['flagged_pairs']:,}", 'HouseBQNoRel': f(H['point']['no_related']), 'HouseBQNoRelCI': ci(H['ci']['no_related']),
         'AddrPairs': f"{A['additional_address_pairs']:,}", 'AddrRemaining': f"{A['remaining_pairs']:,}",
         'AddrOLS': f(A['point']['no_surname_or_address']), 'AddrOLSCI': ci(A['ci']['no_surname_or_address']),
         'AddrChange': f(A['additional_change']['estimate']), 'AddrChangeCI': ci(A['additional_change']['ci']),
         'AddrPersonOLS': f(A['point']['no_surname_or_person_address']), 'AddrPersonOLSCI': ci(A['ci']['no_surname_or_person_address']),
         'AddrShareCash': f"{100 * A['shared_share_of_endpoints']['cash']:.1f}", 'AddrShareFin': f"{100 * A['shared_share_of_endpoints']['financed']:.1f}"}
    (gen / 'related_ext_numbers.tex').write_text('\n'.join('\\newcommand{\\%s}{%s}' % kv for kv in m.items()) + '\n')
    print(json.dumps(m, indent=1), flush=True)


if __name__ == '__main__':
    import sys
    if '--from-results' in sys.argv:
        write_outputs(json.loads((OUT / 'related_party_extensions.json').read_text()))
    else:
        main()
