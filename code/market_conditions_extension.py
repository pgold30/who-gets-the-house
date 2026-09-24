"""Bounded historical inventory exercise and corrected weekly-rate controls.

Uses frozen inputs only. Endpoint-calendar covariance permits shared first/second
periods in any role and includes same-parcel dependence by inclusion-exclusion.
"""
import json
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import t, f
from analyze_repeat_sales import DATA, OUT, ROOT, design, residualize


def meat(scores, keys):
    groups = defaultdict(lambda: np.zeros(scores.shape[1]))
    for s, k in zip(scores, keys):
        groups[k] += s
    return sum((np.outer(s, s) for s in groups.values()), np.zeros((scores.shape[1],) * 2))


def calendar_meat(scores, a, z, parcel=None):
    """Count each ordered observation pair sharing a calendar node exactly once."""
    nodes, edges = defaultdict(lambda: np.zeros(scores.shape[1])), defaultdict(lambda: np.zeros(scores.shape[1]))
    for i, s in enumerate(scores):
        ends = sorted(set((a[i], z[i])))
        prefix = () if parcel is None else (parcel[i],)
        for e in ends:
            nodes[prefix + (e,)] += s
        if len(ends) == 2:
            edges[prefix + tuple(ends)] += s
    zero = np.zeros((scores.shape[1],) * 2)
    return sum((np.outer(v, v) for v in nodes.values()), zero) - sum((np.outer(v, v) for v in edges.values()), zero)


def union_cov(scores, a, z, parcel):
    return calendar_meat(scores, a, z) + meat(scores, parcel) - calendar_meat(scores, a, z, parcel)


def check_covariance():
    # Independent direct enumeration covers reversed endpoints, same-period
    # observations and shared parcels without shared calendar endpoints.
    rng = np.random.default_rng(20260922)
    s = rng.normal(size=(8, 3))
    a = np.array([1, 2, 3, 1, 4, 5, 3, 2]); z = np.array([2, 1, 3, 4, 5, 6, 6, 4])
    p = np.array([0, 1, 2, 3, 0, 4, 5, 2])
    brute = np.zeros((3, 3))
    for i in range(len(s)):
        for j in range(len(s)):
            if p[i] == p[j] or set((a[i], z[i])) & set((a[j], z[j])):
                brute += np.outer(s[i], s[j])
    assert np.allclose(union_cov(s, a, z, p), brute, atol=1e-12)


def diagnostics(beta, covariance, df):
    eigen, vectors = np.linalg.eigh((covariance + covariance.T) / 2)
    psd = (vectors * np.maximum(eigen, 0)) @ vectors.T
    se = np.sqrt(np.maximum(np.diag(psd), 0))
    slopes, vc = beta[2:4], psd[2:4, 2:4]
    wald = float(slopes @ np.linalg.solve(vc, slopes))
    sum_se = float(np.sqrt(np.ones(2) @ vc @ np.ones(2)))
    crit = t.ppf(.975, df)
    return dict(se=se.tolist(), ci_low=(beta-crit*se).tolist(), ci_high=(beta+crit*se).tolist(),
                reference_df=int(df), joint_slopes_p=float(f.sf(wald/2, 2, df)),
                common_slope_restriction_p=float(2*t.sf(abs(slopes.sum()/sum_se), df)),
                raw_min_eigenvalue=float(eigen.min()), clipped_eigenvalues=int((eigen < -1e-12).sum()),
                negative_eigenvalue_mass=float(-eigen[eigen < 0].sum()), covariance=psd.tolist())


def fit(d, X, ma, mz, trends=False, geographic_financing=False):
    fa, fz = d.financed_base_a.to_numpy(), d.financed_base_z.to_numpy()
    nuisance = [ma, mz]  # Weekly/monthly levels not fully absorbed by quarter effects.
    if geographic_financing:
        for borough in ['1', '2', '4']:  # Brooklyn is the reference borough.
            b = d.borough.eq(borough).to_numpy()
            nuisance.extend([fa*b, fz*b])
    if trends:
        for side, flag in [('a', fa), ('z', fz)]:
            tt = (pd.to_datetime(d['date_'+side])-pd.Timestamp('2020-01-01')).dt.days.to_numpy()/365.25
            nuisance.append(flag*tt)
    XX = sparse.hstack([X, sparse.csr_matrix(np.column_stack(nuisance))], format='csr')
    Q = np.column_stack([(fa == 0) & (fz == 1), (fa == 1) & (fz == 0), fa*ma, fz*mz]).astype(float)
    R = np.column_stack([residualize(XX, q) for q in Q.T]); ry = residualize(XX, d.y.to_numpy())
    gram = R.T @ R
    assert np.linalg.matrix_rank(gram) == 4
    inverse = np.linalg.inv(gram); beta = inverse @ (R.T @ ry); e = ry-R@beta
    assert np.max(np.abs(R.T@e)) < 1e-7
    scores = (R@inverse)*e[:, None]; parcel = d.bbl.to_numpy()
    covs = {'parcel': diagnostics(beta, meat(scores, parcel), d.bbl.nunique()-1)}
    for name, frequency in [('endpoint_quarter', 'Q'), ('endpoint_year', 'Y')]:
        a = pd.to_datetime(d.date_a).dt.to_period(frequency).astype(str).to_numpy()
        z = pd.to_datetime(d.date_z).dt.to_period(frequency).astype(str).to_numpy()
        covs[name] = diagnostics(beta, union_cov(scores, a, z, parcel), len(set(a)|set(z))-1)
    return dict(n=len(d), parcels=int(d.bbl.nunique()), beta=beta.tolist(), inference=covs,
                trends=trends, endpoint_financing_borough_controls=geographic_financing,
                residualized_column_norms=np.linalg.norm(R, axis=0).tolist(), gram_condition=float(np.linalg.cond(gram)))


def main():
    check_covariance()
    d = pd.read_csv(DATA/'house_pairs_enriched.csv.gz', dtype={'bbl': str, 'borough': str, 'zipcode': str, 'cd': str})
    d = d[d.permit_free & ~d.lender_high & d.geo_linked].copy().reset_index(drop=True)
    for side in ['a', 'z']:
        d['date_'+side] = pd.to_datetime(d['date_'+side]).dt.date
    assert len(d) == 6006
    X = design(d, 'zipcode', True)
    inv = pd.read_csv(DATA/'streeteasy_totalInventory_Sfr.csv')
    inv = inv[inv.areaType.eq('borough')].set_index('areaName')
    bnames = {'1': 'Manhattan', '2': 'Bronx', '3': 'Brooklyn', '4': 'Queens'}
    logs = np.log2(inv.loc[:, '2015-12':'2025-11'])
    assert logs.shape[1] == 120 and np.isfinite(logs.to_numpy()).all()
    centers = logs.mean(axis=1)
    endpoint = {}
    for side in ['a', 'z']:
        months = (pd.to_datetime(d['date_'+side]).dt.to_period('M')-1).astype(str)
        endpoint[side] = np.array([logs.loc[bnames[b], m]-centers.loc[bnames[b]] for b, m in zip(d.borough, months)])
    rates = pd.read_csv(DATA/'MORTGAGE30US.csv')
    rd = pd.to_datetime(rates.iloc[:, 0]).to_numpy(); rv = rates.iloc[:, 1].to_numpy()
    rr = {}
    for side in ['a', 'z']:
        ix = np.searchsorted(rd, pd.to_datetime(d['date_'+side]).to_numpy(), side='right')-1
        assert (ix >= 0).all()
        rr[side] = rv[ix]-4
    out = {'release': 'WGTH-2026-09-22-R2', 'n': len(d), 'inventory_matched_pairs': int(np.isfinite(endpoint['a']+endpoint['z']).sum()),
           'borrowed_baseline_unchanged': True, 'covariance_unit_test': 'passed',
           'inventory_centers_log2': centers.to_dict(), 'coverage_by_borough': d.borough.value_counts().to_dict(),
           'coefficient_order': ['cash_to_financed', 'financed_to_cash', 'first_financing_x_indicator', 'second_financing_x_indicator'],
           'models': {}}
    for label, values, geographic in [('credit', rr, False), ('inventory', endpoint, True)]:
        for trends in [False, True]:
            name = label+('_trends' if trends else '')
            out['models'][name] = fit(d, X, values['a'], values['z'], trends, geographic)
            b = out['models'][name]['beta']; p = out['models'][name]['inference']['endpoint_quarter']['joint_slopes_p']
            print(name, 'endpoint slopes', np.round(100*np.array(b[2:]), 3), 'quarter joint p', round(p, 4), flush=True)
    (OUT/'market_conditions_extension.json').write_text(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
