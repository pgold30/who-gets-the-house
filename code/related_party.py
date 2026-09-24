"""Related-party transfers and the identity of the cash buyer (v3.0).

A deed whose grantor and grantee share a surname is flagged as a probable
related-party (non-arm's-length) transfer. Such transfers are typically
unfinanced and can be priced below market, so they load on the cash side of
both switching arms and are invisible to the symmetry diagnostic.

Flags use the preserved ACRIS party extract (data/parties.json), natural-person
names in 'SURNAME, GIVEN' form only; company, trust and estate names never
match. The strict flag ignores the 40 most frequent surnames in the extract.
Inference reuses the paper's common parcel bootstrap (seed 20260909, 8,127
clusters, 999 draws), so every estimate here is paired with the headline.
"""
import json, re, time
from collections import Counter, defaultdict
from multiprocessing import get_context
import numpy as np
import pandas as pd
from analyze_repeat_sales import DATA, OUT, SEED, design
from robust_estimators import fit_all, wls, switches, years, multinomials, WORKERS

ENTITY = re.compile(r'\b(LLC|L\.L\.C|INC|CORP|CORPORATION|COMPANY|CO\.|BANK|TRUST|TRUSTEE|TRUSTEES|ESTATE|EXECUTOR|EXECUTRIX|ADMINISTRATOR|'
                    r'ASSOCIATION|FUND|PARTNERS|LP|L\.P|HOLDINGS|REALTY|GROUP|MORTGAGE|FEDERAL|SECRETARY|CITY OF|MANAGEMENT|'
                    r'PROPERTIES|DEVELOPMENT|CAPITAL|ASSOC|N\.A|FSB|SERVICING|REFEREE)\b')
N_COMMON = 40


def surname(name):
    if ENTITY.search(name) or ',' not in name:
        return None
    s = name.split(',')[0].strip()
    return s if len(s) > 1 else None


def flags(d):
    by_doc = defaultdict(lambda: {'1': set(), '2': set()})
    parties = json.loads((DATA / 'parties.json').read_text())
    with_parties = {r['document_id'] for r in parties}  # any party record, company or person
    for r in parties:
        s = surname(r['name'].upper().strip())
        if s:
            by_doc[r['document_id']][r['party_type']].add(s)
    freq = Counter(s for v in by_doc.values() for t in '12' for s in v[t])
    common = {s for s, _ in freq.most_common(N_COMMON)}

    def rel(doc, strict):
        if not isinstance(doc, str) or doc not in by_doc:
            return 0
        g, b = by_doc[doc]['1'], by_doc[doc]['2']
        if strict:
            g, b = g - common, b - common
        return int(bool(g & b))
    for s in 'az':
        d['related_' + s] = [rel(x, False) for x in d['deed_' + s]]
        d['related_strict_' + s] = [rel(x, True) for x in d['deed_' + s]]
        d['party_data_' + s] = [int(isinstance(x, str) and x in with_parties) for x in d['deed_' + s]]
    return d, sorted(common)


_S = {}


def _init(**kw):
    _S.update(kw)


def fit_draw(w):
    X, y, g, Q, samples, splits = _S['X'], _S['y'], _S['g'], _S['Q'], _S['samples'], _S['splits']
    out = {}
    for name, m in samples.items():
        for k, v in fit_all(X[m], Q[m], y[m], g[m], w[m]).items():
            if k != 'huber_iterations':
                out[f'{name}|{k}'] = v
    for name, (m, grp) in splits.items():
        mm = m & (w > 0)
        cf, fc = Q[mm, 0] == 1, Q[mm, 1] == 1; gg = grp[mm]
        QQ = np.column_stack([cf & gg, cf & ~gg, fc & gg, fc & ~gg]).astype(float)
        b, _ = wls(X[mm], QQ, y[mm], w[mm])
        out[f'{name}|company'] = .5 * (b[0] - b[2]); out[f'{name}|other'] = .5 * (b[1] - b[3])
        out[f'{name}|difference'] = out[f'{name}|other'] - out[f'{name}|company']
    return out


def main():
    d = pd.read_csv(DATA / 'house_pairs_enriched.csv.gz', dtype={'bbl': str, 'borough': str, 'zipcode': str, 'cd': str, 'deed_a': str, 'deed_z': str})
    G = int(d.cluster.max() + 1); assert G == 8127
    d = d[d.permit_free & ~d.lender_high & d.geo_linked].copy().reset_index(drop=True)
    for s in ['a', 'z']: d['date_' + s] = pd.to_datetime(d['date_' + s]).dt.date
    assert len(d) == 6006
    d, common = flags(d)
    X = design(d, 'zipcode', True); y = d.y.to_numpy(); Q = switches(d); g = y / years(d); cl = d.cluster.to_numpy()
    fa, fz = d.financed_base_a.to_numpy(), d.financed_base_z.to_numpy()
    cf, fc = Q[:, 0] == 1, Q[:, 1] == 1
    rel = (d.related_a + d.related_z).to_numpy() > 0
    rel_strict = (d.related_strict_a + d.related_strict_z).to_numpy() > 0
    # identity of the buyer at the cash endpoint of a switching pair
    cash_company = np.where(cf, d.buyer_entity_a.astype(bool), np.where(fc, d.buyer_entity_z.astype(bool), False))
    everyone = np.ones(len(d), bool)
    samples = {'all': everyone, 'no_related': ~rel, 'no_related_strict': ~rel_strict}
    splits = {'all': (everyone, cash_company), 'no_related': (~rel, cash_company)}

    desc = {'pairs': len(d), 'party_data_share': {s: float(d['party_data_' + s].mean()) for s in 'az'},
            'related_pairs': int(rel.sum()), 'related_pairs_strict': int(rel_strict.sum()),
            'common_surnames_ignored_by_strict_flag': common}
    ends = pd.concat([pd.DataFrame({'financed': d['financed_base_' + s], 'related': d['related_' + s],
                                    'company_buyer': d['buyer_entity_' + s].astype(bool)}) for s in 'az'])
    desc['related_share_of_endpoints'] = {'cash': float(ends.related[ends.financed == 0].mean()),
                                          'financed': float(ends.related[ends.financed == 1].mean()),
                                          'cash_endpoints': int((ends.financed == 0).sum()), 'financed_endpoints': int((ends.financed == 1).sum())}
    desc['switching_pairs'] = {'cash_to_financed': int(cf.sum()), 'financed_to_cash': int(fc.sum()),
                               'cash_buyer_company': int((cash_company & (cf | fc)).sum()),
                               'related_among_switching': int((rel & (cf | fc)).sum())}
    arm = np.where(cf, 'cash_to_financed', np.where(fc, 'financed_to_cash', 'unchanged'))
    desc['mean_log_growth'] = {a: {'related': float(y[(arm == a) & rel].mean()) if ((arm == a) & rel).any() else None,
                                   'unrelated': float(y[(arm == a) & ~rel].mean()),
                                   'n_related': int(((arm == a) & rel).sum())} for a in np.unique(arm)}
    desc['sample_dates'] = {'first_sale': [str(d.date_a.min()), str(d.date_a.max())], 'resale': [str(d.date_z.min()), str(d.date_z.max())]}

    _init(X=X, y=y, g=g, Q=Q, samples=samples, splits=splits)
    point = fit_draw(np.ones(len(d)))
    assert abs(100 * point['all|ols'] - 9.25) < 0.005
    t = time.monotonic()
    with get_context('fork').Pool(WORKERS) as pool:  # workers inherit _S by fork
        D = pd.DataFrame(pool.map(fit_draw, [w[cl].astype(float) for w in multinomials(G, SEED)], chunksize=8))
    published = json.loads((OUT / 'robust_estimates.json').read_text())['house_zip_year']['ci']['ols']
    assert np.allclose(np.percentile(D['all|ols'], [2.5, 97.5]), published, atol=1e-7)
    res = {'description': desc, 'point': point,
           'ci': {k: np.percentile(D[k], [2.5, 97.5]).tolist() for k in D},
           'difference_from_headline_ols': {k: {'estimate': point[k] - point['all|ols'], 'ci': np.percentile(D[k] - D['all|ols'], [2.5, 97.5]).tolist()}
                                            for k in D if k.endswith('|ols') and k != 'all|ols'},
           'bootstrap': {'draws': len(D), 'seed': SEED, 'clusters': G, 'seconds': time.monotonic() - t},
           'method': 'Same-surname grantor/grantee on the endpoint deed (natural-person names only). Strict flag ignores the %d most frequent surnames. '
                     'Cash-buyer identity: explicit company form of the grantee at the unfinanced endpoint of a switching pair.' % N_COMMON}
    (OUT / 'related_party.json').write_text(json.dumps(res, indent=2))
    d[['bbl', 'deed_a', 'deed_z', 'related_a', 'related_z', 'related_strict_a', 'related_strict_z', 'party_data_a', 'party_data_z']].to_csv(OUT / 'related_party_flags.csv', index=False)
    write_outputs(res)


def write_outputs(res):
    point, desc = res['point'], res['description']
    rel_n, rel_strict_n = desc['related_pairs'], desc['related_pairs_strict']
    rel_share = desc['related_share_of_endpoints']

    f = lambda v: f'{100 * v:.2f}'
    ci = lambda k: '[{:.2f}, {:.2f}]'.format(*(100 * np.array(res['ci'][k])))
    cell = lambda k: f'{f(point[k])} {ci(k)}'
    N = desc['pairs']
    rows = [('All pairs', 'all', N), ('No same-surname deeds', 'no_related', N - rel_n),
            ('Same, strict flag', 'no_related_strict', N - rel_strict_n)]
    body = [f"{lab} & {n:,} & {cell(k + '|ols')} & {cell(k + '|huber')} & {f(point[k + '|trim_1_99'])} & {f(point[k + '|trim_2.5_97.5'])} \\\\" for lab, k, n in rows]
    body2 = [f"{lab} & {n:,} & {cell(k + '|company')} & {cell(k + '|other')} & \\multicolumn{{2}}{{r}}{{{cell(k + '|difference')}}} \\\\" for lab, k, n in rows[:2]]
    tex = r'''\begin{table}[htbp]\centering\footnotesize\setlength{\tabcolsep}{3pt}
\caption{Related-party transfers and the identity of the cash buyer}\label{tab:related}
\begin{tabular}{lrllrr}\toprule
\multicolumn{6}{l}{\textit{A. Financing contrast by estimator}}\\
Sample & Pairs & Least squares & Huber & Trim 1/99 & Trim 2.5/97.5 \\
\midrule
''' + '\n'.join(body) + r'''
\midrule
\multicolumn{6}{l}{\textit{B. Least-squares contrast by the buyer at the cash sale}}\\
Sample & Pairs & Company buyer & Other buyer & \multicolumn{2}{r}{Other minus company} \\
\midrule
''' + '\n'.join(body2) + r'''
\bottomrule\end{tabular}
\notes{Log points; 95\% percentile intervals from the paper's 999 common parcel-bootstrap draws (seed 20260909), with every nuisance control, Huber scale and trimming cutoff re-estimated in each draw. Headline specification of Table~\ref{tab:cumulative}. A same-surname transfer is a deed at either endpoint on which a natural-person grantor and grantee share a surname; company, trust and estate names never match. The strict flag ignores the %d most frequent surnames in the party extract. Panel B splits both switching arms by whether the grantee at the unfinanced sale has an explicit company form; always-financed and always-unfinanced pairs are pooled.}
\end{table}
'''.replace('%d', str(N_COMMON))
    gen = OUT.parent / 'paper/generated'
    (gen / 'related.tex').write_text(tex)
    m = {'RelPairs': f"{desc['related_pairs']:,}", 'RelPairsStrict': f"{desc['related_pairs_strict']:,}",
         'RelShareCash': f"{100 * desc['related_share_of_endpoints']['cash']:.1f}", 'RelShareFin': f"{100 * desc['related_share_of_endpoints']['financed']:.1f}",
         'NoRelOLS': f(point['no_related|ols']), 'NoRelOLSCI': ci('no_related|ols'),
         'NoRelHuber': f(point['no_related|huber']), 'NoRelHuberCI': ci('no_related|huber'),
         'NoRelStrictOLS': f(point['no_related_strict|ols']), 'NoRelStrictOLSCI': ci('no_related_strict|ols'),
         'NoRelMin': f(min(point['no_related|' + k] for k in ['ols', 'huber', 'trim_1_99', 'trim_2.5_97.5'])),
         'NoRelMax': f(max(point['no_related|' + k] for k in ['ols', 'huber', 'trim_1_99', 'trim_2.5_97.5'])),
         'NoRelChange': f(res['difference_from_headline_ols']['no_related|ols']['estimate']),
         'NoRelChangeCI': '[{:.2f}, {:.2f}]'.format(*(100 * np.array(res['difference_from_headline_ols']['no_related|ols']['ci']))),
         'CompanyCash': f(point['all|company']), 'CompanyCashCI': ci('all|company'),
         'OtherCash': f(point['all|other']), 'OtherCashCI': ci('all|other'),
         'CompanyCashNoRel': f(point['no_related|company']), 'CompanyCashNoRelCI': ci('no_related|company'),
         'OtherCashNoRel': f(point['no_related|other']), 'OtherCashNoRelCI': ci('no_related|other'),
         'NoRelInvQTen': f"{100 * np.expm1(point['no_related|ols']) * 9:.0f}",
         'NoRelHuberInvQTen': f"{100 * np.expm1(point['no_related|huber']) * 9:.0f}",
         'RelRatio': f"{rel_share['cash'] / rel_share['financed']:.1f}",
         'RelShareOfGap': f"{100 * (1 - point['no_related|ols'] / point['all|ols']):.0f}",
         'OtherMinusCompanyNoRel': f(point['no_related|difference']), 'OtherMinusCompanyNoRelCI': ci('no_related|difference'),
         'RelGrowthCFRel': f"{desc['mean_log_growth']['cash_to_financed']['related']:.2f}",
         'RelGrowthCFUnrel': f"{desc['mean_log_growth']['cash_to_financed']['unrelated']:.2f}",
         'RelGrowthFCRel': f"{-desc['mean_log_growth']['financed_to_cash']['related']:.2f}",
         'RelGrowthFCUnrel': f"{desc['mean_log_growth']['financed_to_cash']['unrelated']:.2f}",
         'PartyShareA': f"{100 * desc['party_data_share']['a']:.0f}", 'PartyShareZ': f"{100 * desc['party_data_share']['z']:.0f}",
         'CashCompanyPairs': f"{desc['switching_pairs']['cash_buyer_company']:,}",
         'SwitchPairs': f"{desc['switching_pairs']['cash_to_financed'] + desc['switching_pairs']['financed_to_cash']:,}"}
    (gen / 'related_numbers.tex').write_text('\n'.join('\\newcommand{\\%s}{%s}' % kv for kv in m.items()) + '\n')
    print(json.dumps({k: round(100 * v, 2) for k, v in point.items()}), flush=True)
    print(json.dumps(desc, indent=1, default=str)[:3000], flush=True)


if __name__ == '__main__':
    import sys
    if '--from-results' in sys.argv:
        write_outputs(json.loads((OUT / 'related_party.json').read_text()))
    else:
        main()
