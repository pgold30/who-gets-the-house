# Codebook and variable conventions

Release WGTH-2026-09-10. Monetary amounts are nominal US dollars. Dates are ISO dates unless a raw source retains its original format. A BBL is the ten-character borough/block/lot identifier; preserve it as text. Borough codes: 1 Manhattan, 2 Bronx, 3 Brooklyn, 4 Queens, 5 Staten Island. Unknowns are not automatically zero. The scripts document the exact filters in executable form.

## Archived panel: inputs/2_reproduce/panel2.csv.gz

- bbl: matched real-property parcel identifier, including recovered condominium unit lots where the original linkage succeeds.
- date: sale date, YYYY-MM-DD.
- price: recorded sale consideration in dollars.
- borough: borough code as above.
- src: house or condo; property group assigned by the original processing.
- financed_strict, financed_base, financed_wide: binary matched-MTGE indicators using respectively [-15,+30], [-15,+90], [-15,+180] days relative to sale. Zero is no matched mortgage under that rule, not verified absence of borrowing. Document dates with recording-date fallback are used in the legacy pipeline.
- mort_amt: maximum amount of candidate base-window mortgages in the legacy construction, zero if none. It is not verified acquisition loan principal or total indebtedness.
- n_sale: sequence number within the archived eligible parcel sales.
- n_sales_total: number of archived eligible sales for the parcel.

## Archived density sample

inputs/4_full_pipeline/sample_2016_2025.csv.gz contains sale_price, sale_date, borough and bbl. The last may be missing. It lacks property type, apartment and unique transaction identifiers. Identical BBL/date/price tuples can represent separate units; tuple collapse is a sensitivity only.

## Archived permit and deed lookup inputs

DOB source field descriptions are available at https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a. Required fields are borough (name), block, lot and issuance_date (MM/DD/YYYY). The code maps those fields to BBL and considers issuances between the two sale dates inclusively. Other preserved columns are source fields and unused in current estimates; the official dataset metadata defines them.

deeds_for_pairs.json maps each BBL to lists of [document date, document ID]. It supplies candidates for a unique nearest date within 45 days. It does not by itself classify transfer purpose or validate consideration.

## New public extracts

- geo.json: bbl, zipcode, cd (community district), bct2020 (borough/census tract, retained but not used in the final geography controls), version (26v2). Source documentation: NYC PLUTO data dictionary.
- master.json: document_id; doc_type; document_date; document_amt (recorded consideration); recorded_datetime. ACRIS source: bnx9-e6tj.
- parties.json: document_id; party_type (1 grantor/seller, 2 grantee/buyer); name. ACRIS source: 636b-3b5g. Multiple parties per document remain separate rows.
- coop_sales_all.json: source bbl, sale_date, sale_price, address, apartment_number and building-class fields when available. Explicit apartment is preferred; otherwise an address suffix after a comma is normalized. Codes 09, 10 and 17 define the queried co-operative categories. All observed competing sales are considered before restricting eligible price/date/unit coverage.
- coop_inic_master.json: document_id and recorded_datetime for INIC initial personal-property filings. A filing is not necessarily a purchase loan.
- coop_legals.json: document_id, borough, block, lot, and preserved source legal-row fields. Multiple legal rows can belong to one document. More than one distinct parcel excludes the filing from timing-unique assignment. Source uqqa-hym2.
- pmms_web_YEAR.json and *_gap.json: saved official annual page excerpts, including source references and visible line text. These are the input to parse_rates.py, not synthetic rate observations.
- MORTGAGE30US.csv: observation date and annual percentage rate for the weekly 30-year PMMS series. Column names are retained by the parser. data/rates_validation.json records date checks.
- api_cache/*.json: raw response arrays corresponding to the adjacent .url.txt request; upstream field meanings are given by the named NYC Open Data resource. The response is not an independent additional sample.

## Derived house_pairs_enriched.csv.gz

One row is an eligible adjacent archived house pair held at least 1,095 days. Suffix a denotes the initial sale and z the subsequent sale.

- bbl, borough, date_a, date_z: identifiers and endpoints.
- y: log(price_z / price_a).
- cluster: zero-based index of the original parcel cluster, retained consistently across restrictions.
- permit_free: no recorded permit issuance between endpoints.
- zipcode, cd, geo_linked: fixed PLUTO location and a usable geography indicator.
- financed_WINDOW_SIDE: the archived strict/base/wide financing indicator at each endpoint.
- deed_SIDE: uniquely closest document ID within 45 days, empty if unresolved.
- deed_unique_SIDE: one unique closest candidate, not a legal validity determination.
- amount_match_SIDE: positive document amount within max($1, 1% of DOF price).
- buyer_entity_SIDE, seller_entity_SIDE: any explicit company-form or entity-pattern match for the relevant parties.
- buyer_trust_SIDE, seller_trust_SIDE: trust/estate pattern with no overriding entity-pattern match.
- buyer_unknown_SIDE, seller_unknown_SIDE: no usable party names. These enter separate controls.
- buyer_lender_high_SIDE, seller_lender_high_SIDE: named-institution regex flags. The complete HIGH pattern is in analyze_repeat_sales.py.
- buyer_lender_broad_SIDE, seller_lender_broad_SIDE: broader institutional/lending tokens. The BROAD pattern is preserved in the same script.
- lender_high, lender_broad: any corresponding flag across both roles and both dates.
- financing_stable: strict and wide indicators agree at both endpoints.

Buyer/seller controls use the second-minus-first difference of entity, trust and unknown indicators. The residual category is names without those patterns; it is not verified natural-person ownership. The institutional variables never mean adjudicated REO status.

## Co-operative assignment audit

coop_assignment_audit.csv.gz contains bbl, unit_key (BBL plus normalized apartment), sale_day, legacy_k (eligible nearby sale count), all_sales_k, expanded_m (filing count in expanded window), extra_competitors, base_candidate_filings, base_filing_competing_sales and base_unique_candidate_document_id (retained when exactly one candidate exists). Counts refer to the executable windows, not verified borrower matches.

Each method column uses 1 for financed proxy, 0 for no matched filing, and -1 for ambiguous. legacy_expanded compares the expanded filing count with eligible sales. expanded_all_competitors counts all observed competing sales. unique_strict, unique_base and unique_wide require one filing and one possible observed purchase under the corresponding timing window. A unique candidate document ID can be retained even when another sale also claims it; the method label determines whether assignment is timing-unique.

## Review queues

The distress queue samples 30 observations per specific-institution, broad-only and unflagged stratum. The co-operative queue samples 30 per timing-unique, no-filing and ambiguous base-rule stratum. stratum_population is the number of eligible observations in that stratum; selection_probability equals sampled count / stratum population; inverse_probability_weight is its reciprocal. Document links and candidate IDs support review. Ground-truth, evidence and reviewer fields are not populated with inferred answers. All labels are UNREVIEWED in this release.

A review must distinguish an instrument's visible wording from inferred economic circumstances. An ordinary deed can be an REO resale without being a referee's deed. Conversely, a lender token is not proof of distress. Missing decisive evidence is indeterminate, not negative. Co-operative review must verify collateral unit and borrower/purchase identity; timing alone cannot provide the ground truth used to evaluate that timing rule.

## Statistical result fields

- pairs, parcels, cf, fc: estimation pair count, clustering-unit count, cash-to-financed count and financed-to-cash count. Co-operative parcels are buildings.
- pi_residual: half-difference of switching means after residualizing only the outcome.
- pi_joint: half-difference of jointly fitted switching coefficients.
- asym_residual, asym_joint: corresponding sum of switching means or coefficients, subject to their respective reference definitions.
- se_residual, se_joint and ci_*: cluster CR0 standard errors and pointwise 1.96-SE intervals, unless the bootstrap file explicitly supplies percentile intervals.
- beta, beta_se: ordered coefficient and standard-error arrays. Individual result files record interaction coefficient names where applicable.
- nuisance_columns: number of columns in the sparse nuisance design, not an assertion of full column rank.
- switch_information_fraction: residual switching-design trace divided by its unprojected trace; a support diagnostic, not an R-squared for the outcome.
- max_nuisance_score: maximum absolute X' residual score, used to inspect projection accuracy.
- joint_covariance.csv: cross-products of parcel influence functions across all listed specification/estimand combinations.
- paired_specification_differences.csv: from, to, estimand, difference, se, ci_low, ci_high. Covariance between specifications is included.
- paired_full_refit_bootstrap.npy: 999 rows of common parcel-bootstrap draws; column order is in the accompanying JSON labels. Percentile intervals and paired-difference intervals are in that JSON.
- financing_window_agreement.csv: group, label window, sale count, financed share, disagreements with base. Disagreements are not validated errors.

## Robust-estimator and mechanism outputs

robust_estimates.json: for each sample (house_zip_year, house_borough_quarter, condo_borough_quarter), point estimates for ols, huber, trim_1_99 and trim_2.5_97.5 (log points), percentile bootstrap intervals, paired differences from ols, Huber down-weighting shares by switching arm, shares of pairs with log growth above 0.7 by arm, and Huber iteration counts. robust_bootstrap_*.csv: the 999 draws of every estimator.

Credit result files list their coefficient ordering: switching arms first, followed by financing interacted with rate deviations from 4 percent at each sale date, and where included financing-specific calendar trends centered on 2020. Rate coefficients use probability labels and rates in percentage points, not decimal interest rates.

model_inversion_scenarios.json records property, q_failure_scenario, gap_log and implied_d. d = (exp(gap_log)-1)*(1-q)/q. q is an illustrative assumption. publication_numbers.json records the final manuscript macros; it is generated from current results rather than serving as input to estimation.

related_party.json (v3.0): description (pair counts, party-record coverage by endpoint, same-surname shares of cash and financed endpoints, switching-pair counts, mean log growth by arm and flag, sample dates, the 40 surnames ignored by the strict flag), point estimates and 95% percentile intervals (log-price units; multiply by 100 for log points) keyed as sample|estimator for samples all, no_related, no_related_strict and estimators ols, huber, trim_1_99, trim_2.5_97.5, plus sample|company, sample|other and sample|difference for the cash-buyer split; paired differences from the headline least-squares estimate; bootstrap metadata.

related_party_flags.csv (v3.0): one row per headline house pair (bbl, deed_a, deed_z) with related_a/related_z (same-surname flag at each endpoint), related_strict_a/related_strict_z (strict flag) and party_data_a/party_data_z (1 if the endpoint deed has party records).

related_party_extensions.json (v3.1): house_borough_quarter and condo_borough_quarter (pairs, clusters, endpoints, endpoints_with_deed, endpoints_with_party_records, flagged_pairs, flagged_pairs_strict, point and ci for all / no_related / no_related_strict, paired change; condominium deed_linkage from the retrieval manifest); house_shared_address (pair counts, shared-address shares of cash and financed endpoints, point and ci for no_surname / no_surname_or_address / no_surname_or_person_address, additional changes, normalization rule); bootstrap metadata. Values are log-price units.

data/condo_pairs_with_deeds.csv.gz (v3.1): the 6,584 condominium pairs of Table 4 with unit BBL, dates, prices, base financing flags, log growth, cluster and the linked deed document_id at each endpoint (blank when no unique deed within 45 days and 0.5 percent consideration).
data/condo_parties.json.gz (v3.1): ACRIS Real Property Parties rows (document_id, party_type, name) for linked condominium deeds.
data/house_party_addresses.json.gz (v3.1): ACRIS Real Property Parties rows with address_1, city and zip for house endpoint deeds.
