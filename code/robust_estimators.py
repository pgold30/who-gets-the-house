"""Outlier-robust versions of the joint financing contrast.

Robust estimators using conventional tuning constants, all financing-blind in how they treat the outcome:
  - Huber M-estimation (k=1.345) with a two-stage MAD scale (from least-squares
    residuals, then updated once from the first Huber fit), every nuisance
    control refitted inside the iteratively reweighted fit;
  - symmetric trimming of annualized log growth at the 1st/99th and
    2.5th/97.5th percentiles of the estimation sample, cutoffs computed
    without reference to financing labels.
Inference reuses the paper's common parcel bootstrap: same seed, same cluster
count and one multinomial draw per replication, so the OLS row reproduces the
published interval and robust-minus-OLS differences are paired.
"""
import json, os, time
from multiprocessing import get_context
import numpy as np
import pandas as pd
from analyze_repeat_sales import DATA, OUT, REP, SEED, design, residualize
from legacy_estimator import load_panel, build

K_HUBER = 1.345
DRAWS = 999
TRIMS = {'trim_1_99': (1, 99), 'trim_2.5_97.5': (2.5, 97.5)}


def wquantile(v, w, qs):
    o = np.argsort(v); v, w = v[o], w[o]
    c = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp(np.asarray(qs) / 100, c, v)


def wls(X, Q, y, w):
    sw = np.sqrt(w); XX = X.multiply(sw[:, None]).tocsr()
    ry = residualize(XX, y * sw)
    R = np.column_stack([residualize(XX, Q[:, j] * sw) for j in range(Q.shape[1])])
    beta = np.linalg.solve(R.T @ R, R.T @ ry)
    return beta, (ry - R @ beta) / sw


def mad_scale(e, w):
    return wquantile(np.abs(e - wquantile(e, w, [50])[0]), w, [50])[0] / 0.6745


def huber_fixed_scale(X, Q, y, base_w, scale, e):
    """IRLS at a fixed scale: a convex problem, so the iteration converges."""
    beta = None
    for it in range(1000):
        hw = np.minimum(1.0, K_HUBER * scale / np.maximum(np.abs(e), 1e-12))
        new, e = wls(X, Q, y, base_w * hw)
        if beta is not None and np.max(np.abs(new - beta)) < 1e-7:
            return new, e, hw, it + 1
        beta = new
    raise RuntimeError('fixed-scale Huber IRLS did not converge')


def huber(X, Q, y, base_w):
    """Two-stage scale: MAD of least-squares residuals, then one MAD update."""
    _, e = wls(X, Q, y, base_w)
    b, e, hw, i1 = huber_fixed_scale(X, Q, y, base_w, mad_scale(e, base_w), e)
    b, e, hw, i2 = huber_fixed_scale(X, Q, y, base_w, mad_scale(e, base_w), e)
    return b, hw, i1 + i2


def switches(df):
    fa = df.financed_base_a.to_numpy(); fz = df.financed_base_z.to_numpy()
    return np.column_stack([(fa == 0) & (fz == 1), (fa == 1) & (fz == 0)]).astype(float)


def years(df):
    return np.array([(z - a).days / 365.25 for a, z in zip(df.date_a, df.date_z)])


def fit_all(X, Q, y, g, w):
    """All estimators on one (possibly bootstrap-weighted) sample."""
    keep = w > 0; X, Q, y, g, w = X[keep], Q[keep], y[keep], g[keep], w[keep]
    out = {}
    b, _ = wls(X, Q, y, w); out['ols'] = .5 * (b[0] - b[1])
    b, hw, it = huber(X, Q, y, w); out['huber'] = .5 * (b[0] - b[1]); out['huber_iterations'] = it
    for name, (lo, hi) in TRIMS.items():
        cut = wquantile(g, w, [lo, hi]); m = (g >= cut[0]) & (g <= cut[1])
        b, _ = wls(X[m], Q[m], y[m], w[m]); out[name] = .5 * (b[0] - b[1])
    return out


WORKERS = max(1, (os.cpu_count() or 2) - 2)
_S = {}


def _init(X, Q, y, g, cl):
    _S.update(X=X, Q=Q, y=y, g=g, cl=cl)


def _draw(w):
    return fit_all(_S['X'], _S['Q'], _S['y'], _S['g'], w[_S['cl']].astype(float))


def run(label, df, X, G, seed_draws):
    y = df.y.to_numpy(); Q = switches(df); g = y / years(df); cl = df.cluster.to_numpy()
    ones = np.ones(len(df))
    point = fit_all(X, Q, y, g, ones)
    _, hw, iters = huber(X, Q, y, ones)
    arm = np.where(Q[:, 0] == 1, 'cash_to_financed', np.where(Q[:, 1] == 1, 'financed_to_cash', 'unchanged'))
    down = {a: float((hw[arm == a] < 1).mean()) for a in np.unique(arm)}
    tails = {a: float((y[arm == a] > 0.7).mean()) for a in np.unique(arm)}
    ff = np.array([(fa, fz) == (1, 1) for fa, fz in zip(df.financed_base_a, df.financed_base_z)])
    tails['always_financed'] = float((y[ff] > 0.7).mean())
    t = time.monotonic()
    with get_context('fork').Pool(WORKERS, initializer=_init, initargs=(X, Q, y, g, cl)) as pool:
        draws = pool.map(_draw, seed_draws, chunksize=8)
    D = pd.DataFrame(draws)
    res = {'pairs': len(df), 'cash_to_financed': int(Q[:, 0].sum()), 'financed_to_cash': int(Q[:, 1].sum()),
           'point': point, 'ci': {k: np.percentile(D[k], [2.5, 97.5]).tolist() for k in D if k != 'huber_iterations'},
           'bootstrap_huber_iterations_max': int(D.huber_iterations.max()), 'bootstrap_huber_iterations_median': float(D.huber_iterations.median()),
           'difference_from_ols': {k: {'estimate': point[k] - point['ols'],
                                       'ci': np.percentile(D[k] - D['ols'], [2.5, 97.5]).tolist()} for k in D if k not in ('ols', 'huber_iterations')},
           'huber_iterations': iters, 'huber_share_downweighted_by_arm': down, 'share_log_growth_above_0.7': tails,
           'bootstrap_draws': len(D), 'bootstrap_seconds': time.monotonic() - t}
    point.pop('huber_iterations'); D = D.drop(columns='huber_iterations')
    print(label, json.dumps({k: round(100 * v, 2) for k, v in point.items()}), 'huber iterations max', res['bootstrap_huber_iterations_max'], round(res['bootstrap_seconds']), 's', flush=True)
    return res, D


def multinomials(G, seed):
    rng = np.random.default_rng(seed)
    return [rng.multinomial(G, np.repeat(1 / G, G)) for _ in range(DRAWS)]


def main():
    results = {}
    # Headline specification: identical sample, design and bootstrap draws.
    d = pd.read_csv(DATA / 'house_pairs_enriched.csv.gz', dtype={'bbl': str, 'borough': str, 'zipcode': str, 'cd': str})
    G = int(d.cluster.max() + 1); assert G == 8127
    d = d[d.permit_free & ~d.lender_high & d.geo_linked].copy().reset_index(drop=True)
    for s in ['a', 'z']: d['date_' + s] = pd.to_datetime(d['date_' + s]).dt.date
    assert len(d) == 6006
    res, D = run('house_zip_year', d, design(d, 'zipcode', True), G, multinomials(G, SEED))
    assert abs(100 * res['point']['ols'] - 9.25) < 0.005
    published = json.loads((OUT / 'paired_full_refit_bootstrap.json').read_text())['ci']['S6_zip_year|joint']
    assert np.allclose(res['ci']['ols'], published, atol=1e-7), (res['ci']['ols'], published)
    results['house_zip_year'] = res; D.to_csv(OUT / 'robust_bootstrap_house_zip_year.csv', index=False)
    # Common borough-quarter comparison of houses and condominiums (Table 3).
    rows, _ = load_panel(REP / '2_reproduce')
    for typ in ['house', 'condo']:
        recs = []
        for a, z, da, dz in build([r for r in rows if r['src'] == typ], int(36 * 30.44)):
            r = {'bbl': a['bbl'], 'borough': a['borough'], 'date_a': da, 'date_z': dz, 'y': np.log(float(z['price']) / float(a['price']))}
            for side, s in [('a', a), ('z', z)]: r[f'financed_base_{side}'] = int(s['financed_base'])
            recs.append(r)
        df = pd.DataFrame(recs); _, df['cluster'] = np.unique(df.bbl, return_inverse=True)
        Gt = int(df.cluster.max() + 1)
        res, D = run(typ + '_borough_quarter', df, design(df), Gt, multinomials(Gt, SEED))
        results[typ + '_borough_quarter'] = res; D.to_csv(OUT / f'robust_bootstrap_{typ}_borough_quarter.csv', index=False)
    results['method'] = {'huber_k': K_HUBER, 'scale': 'two-stage MAD/0.6745: from least-squares residuals, then updated once from the first fixed-scale Huber fit; each stage solved to convergence',
                         'trimming': 'annualized log growth, percentile cutoffs from the estimation sample, financing-blind',
                         'bootstrap': 'percentile intervals; common multinomial parcel draws, seed %d; cutoffs and Huber scale re-estimated in every draw' % SEED,
                         'status': 'Conventional default tuning constants; not tuned on the financing contrast.'}
    (OUT / 'robust_estimates.json').write_text(json.dumps(results, indent=2))

    G_ = OUT.parent / 'paper/generated'; f = lambda v: f'{100 * v:.2f}'
    ci = lambda c: f'[{100 * c[0]:.2f}, {100 * c[1]:.2f}]'
    names = [('ols', 'Least squares (reference)'), ('huber', 'Huber M-estimator'),
             ('trim_1_99', 'Trim growth at 1st/99th pct.'), ('trim_2.5_97.5', 'Trim growth at 2.5th/97.5th pct.')]
    H, Hh, Hc = results['house_zip_year'], results['house_borough_quarter'], results['condo_borough_quarter']
    body = []
    for k, lab in names:
        diff = '' if k == 'ols' else f"{f(H['difference_from_ols'][k]['estimate'])} {ci(H['difference_from_ols'][k]['ci'])}"
        body.append(f"{lab} & {f(H['point'][k])} & {ci(H['ci'][k])} & {diff} & {f(Hh['point'][k])} & {f(Hc['point'][k])} \\\\")
    tex = r'''\begin{table}[htbp]\centering\footnotesize\setlength{\tabcolsep}{3pt}
\caption{Outlier-robust estimates of the financing contrast}\label{tab:robust}
\begin{tabular}{lrrrrr}\toprule
 & \multicolumn{3}{c}{Houses, full controls (6,006 pairs)} & \multicolumn{2}{c}{Borough-quarter only} \\
\cmidrule(lr){2-4}\cmidrule(lr){5-6}
Estimator & Contrast & 95\% CI & Change from LS & Houses & Condos \\
\midrule
''' + '\n'.join(body) + r'''
\bottomrule\end{tabular}
\notes{Log points. Columns 2--4 use the headline specification of Table~\ref{tab:cumulative} (ZIP-year and borough-quarter effects, buyer and seller type controls). Columns 5--6 use the common specification of Table~\ref{tab:property}. The Huber estimator ($k=1.345$; MAD scale from least-squares residuals, updated once) refits all nuisance controls by iteratively reweighted least squares. Trimming removes pairs whose annualized log growth lies outside the stated percentiles of the estimation sample; cutoffs ignore financing labels. Intervals are percentile intervals from the same 999 parcel-bootstrap draws as Table~\ref{tab:cumulative}, re-estimating the Huber scale and trimming cutoffs in every draw; the change column is the paired difference within draws. Tuning constants are conventional defaults and were not varied.}
\end{table}
'''
    (G_ / 'robust.tex').write_text(tex)
    m = {'RobustHuber': H['point']['huber'], 'RobustTrimOne': H['point']['trim_1_99'], 'RobustTrimTwo': H['point']['trim_2.5_97.5'],
         'RobustHouseBQHuber': Hh['point']['huber'], 'RobustCondoBQHuber': Hc['point']['huber']}
    lines = ['\\newcommand{\\' + k + '}{' + f(v) + '}' for k, v in m.items()]
    lines += ['\\newcommand{\\RobustHuberCI}{' + ci(H['ci']['huber']) + '}',
              '\\newcommand{\\RobustCondoBQHuberCI}{' + ci(Hc['ci']['huber']) + '}',
              '\\newcommand{\\RobustHouseBQHuberCI}{' + ci(Hh['ci']['huber']) + '}',
              '\\newcommand{\\RobustHuberDown}{' + f"{100 * H['huber_share_downweighted_by_arm']['cash_to_financed']:.0f}" + '}',
              '\\newcommand{\\TailCF}{' + f"{100 * H['share_log_growth_above_0.7']['cash_to_financed']:.0f}" + '}',
              '\\newcommand{\\TailFF}{' + f"{100 * H['share_log_growth_above_0.7']['always_financed']:.0f}" + '}',
              '\\newcommand{\\RobustHouseInvQTen}{' + f"{100 * np.expm1(H['point']['huber']) * 9:.0f}" + '}',
              '\\newcommand{\\RobustMin}{' + f(min(H['point'][k] for k in ['huber', 'trim_1_99', 'trim_2.5_97.5'])) + '}',
              '\\newcommand{\\RobustMax}{' + f(max(H['point'][k] for k in ['huber', 'trim_1_99', 'trim_2.5_97.5'])) + '}']
    (G_ / 'robust_numbers.tex').write_text('\n'.join(lines) + '\n')
    print('Robust estimates, table and macros built.', flush=True)


if __name__ == '__main__':
    main()
