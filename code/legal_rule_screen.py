"""Lender take-title deeds in the headline house sample (v3.2).

Applies the companion paper's party-name classifier (When a Deed Is Not a
Market Sale, module version 1.1.0, vendored unchanged in code/vendor/) to the
deed linked to each endpoint of the 6,006 headline house pairs. A pair is
flagged when either endpoint deed is a referee's deed to a lender, another
conveyance to a lender (such as a deed in lieu) or a lender-to-lender
transfer: events whose recorded consideration can follow a legal rule rather
than a negotiated price. Lender resales and third-party auction purchases are
not flagged.

The classifier's error rates are not yet measured; its own document review is
pending. The screen is a sensitivity, not a correction. Inference reuses the
paper's common parcel bootstrap (seed 20260909, 8,127 clusters, 999 draws), so
every estimate is paired with the headline.
"""
import json, sys, time
from collections import defaultdict
from multiprocessing import get_context
from pathlib import Path
import numpy as np
import pandas as pd
from analyze_repeat_sales import DATA, OUT, SEED, design
from robust_estimators import fit_all, switches, years, multinomials, WORKERS
from related_party import flags

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))
import acris_consideration_filter as acf  # noqa: E402

assert acf.__version__ == '1.1.0'
_S = {}


def events(broad):
    parties = defaultdict(lambda: {'1': [], '2': []})
    for r in json.loads((DATA / 'parties.json').read_text()):
        if r['party_type'] in ('1', '2'):
            parties[r['document_id']][r['party_type']].append(r['name'])
    return {doc: acf.classify_deed(v['1'], v['2'], broad=broad)['event'] for doc, v in parties.items()}


def fit_draw(w):
    X, y, g, Q, samples = _S['X'], _S['y'], _S['g'], _S['Q'], _S['samples']
    out = {}
    for name, m in samples.items():
        for k, v in fit_all(X[m], Q[m], y[m], g[m], w[m]).items():
            if k != 'huber_iterations':
                out[f'{name}|{k}'] = v
    return out


def main():
    d = pd.read_csv(DATA / 'house_pairs_enriched.csv.gz', dtype={'bbl': str, 'borough': str, 'zipcode': str, 'cd': str, 'deed_a': str, 'deed_z': str})
    G = int(d.cluster.max() + 1); assert G == 8127
    d = d[d.permit_free & ~d.lender_high & d.geo_linked].copy().reset_index(drop=True)
    for s in ['a', 'z']: d['date_' + s] = pd.to_datetime(d['date_' + s]).dt.date
    assert len(d) == 6006
    d, _ = flags(d)
    rel = ((d.related_a + d.related_z) > 0).to_numpy()
    legal = {}
    desc = {'pairs': len(d), 'classifier_version': acf.__version__}
    for label, broad in [('narrow', False), ('broad', True)]:
        ev = events(broad)
        ea, ez = d.deed_a.map(ev), d.deed_z.map(ev)
        la, lz = ea.isin(acf.NONMARKET).to_numpy(), ez.isin(acf.NONMARKET).to_numpy()
        legal[label] = la | lz
        Q = switches(d)
        fin = {s: d['financed_base_' + s].to_numpy() for s in 'az'}
        desc[label] = {'pairs_flagged': int(legal[label].sum()),
                       'endpoints_flagged': int(la.sum() + lz.sum()),
                       'flagged_endpoints_unfinanced': int((la & (fin['a'] == 0)).sum() + (lz & (fin['z'] == 0)).sum()),
                       'flagged_at_first_sale': int(la.sum()), 'flagged_at_resale': int(lz.sum()),
                       'flagged_cash_to_financed': int((legal[label] & (Q[:, 0] == 1)).sum()),
                       'flagged_financed_to_cash': int((legal[label] & (Q[:, 1] == 1)).sum()),
                       'flagged_and_broad_institution_rule': int((legal[label] & d.lender_broad.to_numpy()).sum()),
                       'flagged_and_same_surname': int((legal[label] & rel).sum()),
                       'event_counts': pd.concat([ea[la], ez[lz]]).value_counts().to_dict()}
    X = design(d, 'zipcode', True); y = d.y.to_numpy(); Q = switches(d); g = y / years(d); cl = d.cluster.to_numpy()
    everyone = np.ones(len(d), bool)
    samples = {'all': everyone, 'no_legal': ~legal['narrow'], 'no_legal_broad': ~legal['broad'],
               'no_related': ~rel, 'no_legal_no_related': ~legal['narrow'] & ~rel}
    _S.update(X=X, y=y, g=g, Q=Q, samples=samples)
    point = fit_draw(np.ones(len(d)))
    assert abs(100 * point['all|ols'] - 9.25) < 0.005
    t = time.monotonic()
    with get_context('fork').Pool(WORKERS) as pool:
        D = pd.DataFrame(pool.map(fit_draw, [w[cl].astype(float) for w in multinomials(G, SEED)], chunksize=8))
    published = json.loads((OUT / 'robust_estimates.json').read_text())['house_zip_year']['ci']['ols']
    assert np.allclose(np.percentile(D['all|ols'], [2.5, 97.5]), published, atol=1e-7)
    res = {'description': desc, 'point': point,
           'pairs': {k: int(v.sum()) for k, v in samples.items()},
           'ci': {k: np.percentile(D[k], [2.5, 97.5]).tolist() for k in D},
           'difference_from_headline_ols': {k: {'estimate': point[k] - point['all|ols'], 'ci': np.percentile(D[k] - D['all|ols'], [2.5, 97.5]).tolist()}
                                            for k in D if k.endswith('|ols') and k != 'all|ols'},
           'difference_from_no_related_ols': {'estimate': point['no_legal_no_related|ols'] - point['no_related|ols'],
                                              'ci': np.percentile(D['no_legal_no_related|ols'] - D['no_related|ols'], [2.5, 97.5]).tolist()},
           'bootstrap': {'draws': len(D), 'seed': SEED, 'clusters': G, 'seconds': time.monotonic() - t}}
    (OUT / 'legal_rule_screen.json').write_text(json.dumps(res, indent=2, default=str))
    write_outputs(res)


def write_outputs(res):
    point, desc = res['point'], res['description']
    f = lambda v: f'{100 * v:.2f}'
    ci = lambda k: '[{:.2f}, {:.2f}]'.format(*(100 * np.array(res['ci'][k])))
    dci = lambda v: '[{:.2f}, {:.2f}]'.format(*(100 * np.array(v['ci'])))
    diff = res['difference_from_headline_ols']
    m = {'LegalPairs': f"{desc['narrow']['pairs_flagged']:,}", 'LegalPairsBroad': f"{desc['broad']['pairs_flagged']:,}",
         'LegalEnds': f"{desc['narrow']['endpoints_flagged']:,}", 'LegalEndsCash': f"{desc['narrow']['flagged_endpoints_unfinanced']:,}",
         'LegalCF': f"{desc['narrow']['flagged_cash_to_financed']:,}", 'LegalFC': f"{desc['narrow']['flagged_financed_to_cash']:,}",
         'LegalNotBroad': f"{desc['narrow']['pairs_flagged'] - desc['narrow']['flagged_and_broad_institution_rule']:,}",
         'NoLegalOLS': f(point['no_legal|ols']), 'NoLegalOLSCI': ci('no_legal|ols'),
         'NoLegalChange': f(diff['no_legal|ols']['estimate']), 'NoLegalChangeCI': dci(diff['no_legal|ols']),
         'NoLegalHuber': f(point['no_legal|huber']), 'NoLegalHuberCI': ci('no_legal|huber'),
         'NoLegalBroadOLS': f(point['no_legal_broad|ols']), 'NoLegalBroadOLSCI': ci('no_legal_broad|ols'),
         'NoLegalNoRelOLS': f(point['no_legal_no_related|ols']), 'NoLegalNoRelOLSCI': ci('no_legal_no_related|ols'),
         'NoLegalNoRelChange': f(res['difference_from_no_related_ols']['estimate']),
         'NoLegalNoRelChangeCI': dci(res['difference_from_no_related_ols'])}
    gen = OUT.parent / 'paper/generated'
    (gen / 'legal_numbers.tex').write_text('\n'.join('\\newcommand{\\%s}{%s}' % kv for kv in m.items()) + '\n')
    print(json.dumps(m, indent=1), flush=True)
    print(json.dumps(desc, indent=1, default=str), flush=True)


if __name__ == '__main__':
    if '--from-results' in sys.argv:
        write_outputs(json.loads((OUT / 'legal_rule_screen.json').read_text()))
    else:
        main()
