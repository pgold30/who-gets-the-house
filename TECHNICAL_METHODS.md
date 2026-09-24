# Estimands, sample construction and inference

## House pairs

Inputs are the four-borough archived house panel and DOB permits. Within a parcel, sort the archived eligible sales and consider consecutive observations. Retain a holding period of at least `int(36*30.44) = 1095` days. This reproduces 8,208 original pairs and 6,316 permit-free pairs. The archived panel itself is price/sample restricted; adjacency in that panel is not proof that there were no excluded underlying transfers.

Let y = log(P_second) - log(P_first). Each borough-quarter or local-year index column is the second-date indicator minus the first-date indicator. The 2016 baseline is omitted. Borough-quarter and local-year columns can be redundant; sparse least squares obtains their projection without assigning an economic meaning to an arbitrary individual nuisance coefficient. Column scaling is used for numerical stability and convergence is checked.

Buyer/seller controls are changes between dates in entity, trust/estate and unknown-party indicators. Explicit entity-pattern matches take precedence over trust/estate matches. Thus, these are reproducible name-based party categories, not verified beneficial ownership. A pair with an identifiable financial institution as a grantor or grantee at either date is excluded in the narrower institutional sensitivity. Broad-name exclusions are reported separately.

## Two estimands

For nuisance design X, write M_X for its residual maker. The original contrast is

    pi_residual = c' M_X y,
    c_i = 0.5 * (1{cash->financed}/N_cf - 1{financed->cash}/N_fc).

For Q containing the two switching indicators, the jointly fitted coefficients are

    beta = (Q' M_X Q)^(-1) Q' M_X y,
    pi_joint = (beta_cf - beta_fc)/2.

These are distinct statistical functionals. A decline in the first does not show that covariates explain the second. No maintained exclusion restriction here turns either into a causal execution premium. The asymmetric joint contrast is beta_cf + beta_fc, relative to the same-financing reference observations in the repeat-sales design.

## Influence functions and paired inference

Let r = M_X y, m = M_X c and r_cf/r_fc denote residual means in the two switching arms. The derivative of pi_residual with respect to observation weight i is

    IF_i = m_i*r_i
           - 0.5*1{cf}_i*r_cf/N_cf
           + 0.5*1{fc}_i*r_fc/N_fc.

This includes the refitted market-index response and changing arm denominators. For the joint estimator, let R = M_X Q and e = M_X y - R*beta. The coefficient derivative is

    IF_beta_i = (R'R)^(-1) R_i' e_i.

Apply the half-difference contrast and sum observation derivatives within the original parcel. Each specification's excluded parcels receive zero influence. Stacking those parcel influences across all specifications produces the full covariance matrix, including overlapping-sample covariance. The reported analytic covariance is the uncorrected cluster sandwich (CR0); it is asymptotic and pointwise. It does not automatically account for classification uncertainty or few-cell bias. ZIP-cluster sensitivity is provided for the linked baseline and full geographic model.

Numerical checks perturb five actual parcel weights and refit the full ZIP-year design; both analytic derivatives agree with finite differences to within 1e-7. Full-resampling checks draw multinomial weights over all 8,127 original house parcels (seed 20260909), reuse each draw across the original, permit-free, linked-party-control and ZIP-year specifications, and refit every index/control model. There are 999 draws. The high-dimensional residual statistic shows a resampling location shift; its percentile intervals should not be used to turn attenuation into an explained component. The joint coefficient is the preferred comparison.

## Geography

The current PLUTO 26v2 extract contains 8,087 linked parcels, covering 8,167 pairs. ZIP and community-district identifiers are fixed geographic crosswalks. Geography comparisons use identical linked pairs. Community-district-year and ZIP-year specifications are alternatives, each on top of borough-quarter effects. Fine cells are retained and their support is reported; no precision is manufactured by suppressing sparse-cell information.

## Public-record linkage

Deed candidates come from the archived deed map. Select a unique closest document date within 45 days. Reject tied closest documents as unresolved. New party/master data were retrieved for all closest candidate documents, with bounded requests and assertions against the 50,000-record limit. The consideration check requires a positive document amount within max($1, 1% of sale price). This is not proof that an ambiguous or multi-interest sale is correctly linked. Party-name patterns and their flags are saved, as is a stratified 90-sale review queue; no adjudicated distress labels exist in this package.

## Co-op audit

Retrieve all publicly available co-op sales in the queried date range, including out-of-band prices and records without recoverable units. Recover the unit from the explicit apartment field or the post-comma address suffix, normalize case/whitespace, and audit duplicate stored records. Obtain INIC recording dates from the personal-property master and link through legals; exclude documents touching multiple distinct parcels. Count-complete offset pagination preserves repeated document IDs across legals page boundaries.

Compare (a) the reconstructed expanded count rule, (b) that rule with all competing sales, and (c) narrow/base/wide timing-unique rules. Uniqueness requires one eligible filing for the purchase and one eligible observed sale for that filing; it never establishes borrower identity. In the new pair construction, all observed known-unit sales determine adjacency before financing ambiguity and endpoint eligibility are applied. Unit recovery itself and unrecorded/missing transfers remain limitations. Building-level clustering accounts for dependence between co-op units sharing filing assignment opportunities. The original rule was reconstructed on a fresh, explicitly restricted audit universe, not reproduced on unavailable archived co-op microdata.

## Credit analyses

Rates are the last available weekly Freddie Mac 30-year rate on or before each sale date. Separate F_first*(r_first-4) and F_second*(r_second-4) terms avoid attaching the credit measure only to the resale. An additional specification includes separate financing-specific linear calendar trends centered on 2020. Intercepts across those models have different reference values and are not directly comparable to an unconditional average gap. The observed slope reversal is reported, not selected away.

## Outlier-robust estimators (R3)

code/robust_estimators.py re-estimates the joint contrast of equation (1) with estimators fixed before fitting. The Huber M-estimator uses tuning constant k=1.345 and a two-stage MAD/0.6745 scale: the scale is first computed from least-squares residuals, the fixed-scale Huber problem is solved by iteratively reweighted least squares, the scale is updated once from those residuals, and the problem is solved again. Each fixed-scale problem is convex and is iterated to a maximum coefficient change of 1e-7. (Re-estimating the scale at every iteration was tried first and cycled without converging in some bootstrap draws.) Every nuisance control is refitted inside each weighted fit. Trimming removes pairs whose annualized log growth (log price ratio divided by years between sales) lies outside the 1st/99th or 2.5th/97.5th percentiles of the estimation sample. Neither rule uses financing labels. Intervals are percentiles over the same 999 multinomial parcel draws (seed 20260909, 8,127 clusters) used for the least-squares bootstrap, so the least-squares row reproduces the published interval exactly (asserted in the code) and robust-minus-least-squares differences are paired within draws. The Huber scale and trimming cutoffs are re-estimated in every draw. The same estimators are applied to the common borough-quarter house and condominium samples.


## September 22 market-condition extension

For pair i, the target columns are CF, FC, F_a*m_a and F_z*m_z. The nuisance design includes existing market and party controls plus m_a and m_z separately. Inventory models add endpoint financing-by-borough terms (Brooklyn omitted); trend versions add F_a*t_a and F_z*t_z. Residualize both outcomes and targets on the entire nuisance design, solve the joint normal equations, and form observation coefficient influences from the fitted residuals. Inventory is prior-month log2 inventory centered within borough on December 2015-November 2025; rate is latest weekly PMMS on/before sale minus 4 percentage points.

Let C_T be the sum of outer products of scores aggregated at each endpoint time node, less outer products aggregated on each unordered distinct pair of endpoint nodes. This counts an observation pair with either endpoint in common exactly once, including observations whose two endpoints are in the same node. Let C_P be ordinary parcel clustering and C_TP the same time construction within parcels. The union covariance is C_T + C_P - C_TP. A direct double-sum test checks the construction against the indicator of any shared time node or parcel. Quarter and year versions are both reported. Truncating negative eigenvalues is disclosed; t/F reference distributions use number of calendar nodes minus one, with no claim of exact small-sample size control or protection from arbitrary serial dependence.
