# Replication README

Who Gets the House? Related-Party Transfers and the Cash–Mortgage Price Gap in New York City

Pablo Loschi, independent researcher, Berlin. Contact: loschi.pablo@gmail.com. Version 3.2 (WGTH-2026-09-25-V3.2), prepared 25 September 2026. This self-contained package accompanies paper/paper.pdf for Journal of Housing Economics. It requires no earlier revision folders. Nothing has been submitted or uploaded by this workflow.

## Computational scope and unresolved omissions

The offline analysis run reproduces the baseline calculations from the four supplied archived inputs and preserved public-data extracts. It rebuilds enriched house pairs, co-operative assignments, estimates, covariance, 999 bootstrap refits, numerical checks, outlier-robust re-estimates, seven main-text and appendix computational tables, one figure and the conditional model grid. It does not reconstruct the original house/condominium panel from the full raw DOF/ACRIS extract. That exact raw vintage is absent from the supplied local files and linked GitHub snapshot. No non-public-data exemption or editor-approved waiver is claimed.

The original raw-stage scripts are preserved under legacy_raw_pipeline for provenance, but contain historical paths and an incomplete retrieval-to-analysis integration. Their retrieval wrapper writes NDJSON while linkage scripts expect other filenames/formats, and it is not the master script for this revision. Refreshing today's APIs is a new data vintage, not proof of exact reconstruction of the original extract. Recovering the original raw inputs and running an integrated raw build remains necessary before claiming full raw-to-paper replication.

The consolidated audit includes AI-assisted image review of two house and two co-operative cases, with independent human review pending. One co-operative filing pledges a different unit from its assigned sale; that sale enters no repeat pair and its rejection does not change the estimates. The 90+90 queues remain incomplete. Saved evidence and case notes are in audit; no population accuracy rate or classification-adjusted estimate is claimed. These remain substantive measurement limitations.

## Provenance of the four archived inputs

All four files under inputs are byte-identical to the author's repository https://github.com/pgold30/who-gets-the-house at commit f404e48320a81e3bfe20127af2ed7c2d9fb5268e, retrieved 10 September 2026. Their individual SHA-256 comparisons are in provenance/github_input_comparison.json. This immutable commit identifies the consulted source; it is not a substitute for a trusted repository deposit with a permanent identifier.

- inputs/2_reproduce/panel2.csv.gz: archived merged house/condominium panel; 290,840 sales, including 249,395 outside Staten Island. SHA-256 a99671affb4d16190e064a998f62541bffa3976bcd432cfd365ff26ddcc8a6c5.
- inputs/2_reproduce/dob_permits.csv.gz: original permit snapshot. SHA-256 1785534a084b78ae117d94c5997944b65b0d03a00aa51734570b7a26b4cb2baf.
- inputs/3_section4.9/deeds_for_pairs.json: original date/document lookup for house parcels. SHA-256 5a3914253109fd3cf3c097de7660121363e051168257b6a688521777f7f4b349.
- inputs/4_full_pipeline/sample_2016_2025.csv.gz: archived 431,471-sale citywide price sample. Not used by this manuscript version: the transfer-tax threshold analysis it supported is reported in the companion paper (The Shape of the Tax, replication doi:10.5281/zenodo.22880953) and has been removed here. SHA-256 495d66ab48b781fc6b0d02015b15ecf6049a1843e255e0a23f6786ef264bced9.

The parent release is publicly deposited at https://doi.org/10.5281/zenodo.22915008, version v2.1 (concept DOI: 10.5281/zenodo.22421850). Both the local September 22 ZIP and manuscript match the deposited checksums. This folder prepares a new local revision (v2.2); it has not been uploaded. The separate tax project at https://doi.org/10.5281/zenodo.22880954 is not the parent of this paper. Use the instructions here and the prepared replacement metadata.

## Data availability and source citations

The following public administrative sources were accessed without credentials or a purchase fee. Fresh-extract metadata and per-request URLs are preserved in data, including API cache request files. Existing public endpoints can change: use the supplied extracts for this version and a separate directory for any refresh. Approximate original full-source retrieval is tens of gigabytes and hours according to the legacy repository; the completed current extract package is about 0.4 GB uncompressed. Network speed, throttling and public updates affect retrieval time.

NYC Department of Finance (2026), Annualized Calendar Sales, resource w2pb-icbu, https://data.cityofnewyork.us/resource/w2pb-icbu.json. The archived price sample covers 2016-2025. data/coop_sales_all.json preserves the new broader co-operative extract, including out-of-band prices and incomplete-unit records needed to identify competitors. The fresh extract is not assumed to equal unavailable legacy co-operative microdata.

NYC Department of Finance (2026), ACRIS Real Property Master, Legals and Parties, resources bnx9-e6tj, 8h5j-fqxa and 636b-3b5g. Public endpoints follow https://data.cityofnewyork.us/resource/RESOURCE.json. data/master.json and data/parties.json contain the targeted deed enrichment. The full original master/legals extract that generated the archived panel is not supplied. ACRIS documentation: https://www.nyc.gov/site/finance/property/acris.page.

NYC Department of Finance (2026), ACRIS Personal Property Master and Legals, resources sv7x-dduq and uqqa-hym2. data/coop_inic_master.json and data/coop_legals.json preserve initial-filing records and their parcel linkage. Master records are linked to legal rows, with multi-parcel instruments excluded from timing-unique assignment. Count-checked offset pagination preserves repeated document identifiers across legal rows.

NYC Department of Buildings (2026), DOB Permit Issuance, resource ipu4-2q9a, https://data.cityofnewyork.us/resource/ipu4-2q9a.json. The archived CSV supplies permit issuance dates; qualifying dates from 2010 onward are used to check pair intervals. It is not a complete measure of renovation or permit completion.

NYC Department of City Planning (2026), PLUTO version 26v2, resource 64uk-42ks, https://data.cityofnewyork.us/resource/64uk-42ks.json. data/geo.json preserves targeted geography for 8,087 parcels and links 8,167 house pairs. ZIP and community district are fixed crosswalks, not historical attributes. General documentation: https://www.nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page.

Freddie Mac (2026), Primary Mortgage Market Survey historical archives, https://www.freddiemac.com/pmms/pmms_archives. The preserved annual web extracts and gap-filling excerpts cover all 574 weekly 30-year observations in 2015-2025. code/parse_rates.py reconstructs data/MORTGAGE30US.csv and checks date coverage. The filename is a familiar series identifier; the actual source here is the Freddie Mac archive, not a successful FRED bulk download. Direct bulk routes returned HTTP errors, so original official page extracts were saved. The methodology changed on 17 November 2022. Values are percent per year; the latest available week on or before each sale is used.

## Access, redistribution and licences

The included City extracts were legitimately accessed through public NYC Open Data endpoints. Redistribution and reuse follow the City's published public-data terms, including identification of source, vintage and modifications: https://cityofnewyork.github.io/opendatatsm/publicpolicies.html. City source records are not re-licensed as the author's original work. The City does not endorse these estimates and supplies no warranty for them.

The Freddie Mac archive permits use of its information with attribution and retains its copyright and conditions. The package preserves the supplied source extracts and separately identifies the parsed rate series. No blanket author licence is asserted over Freddie Mac materials. Its current source notice is linked above.

Author code is provided under MIT and author-created documentation and compilation contributions under CC-BY-4.0, consistent with the supplied repository's licence statement. These permissions apply only to rights the author holds; underlying source terms remain in force. See LICENSE_CODE.txt and THIRD_PARTY_NOTICES.md. This package may be used to replicate the research. No confidential source, paid data agreement, or human-subject experiment is represented as part of this release.

## Software, environment and runtime

Validated environment: Python 3.12.14 in a newly created virtual environment, macOS 26.6.2 on arm64 with 8 logical CPUs. User site packages were disabled and PYTHONPATH and PYTHONHOME unset. NumPy 2.5.3, pandas 2.2.3, SciPy 1.18.1, Matplotlib 3.11.1, ReportLab 4.4.9 and pypdf 6.10.0 were installed from scratch. requirements-lock.txt pins all installed dependency versions. Tectonic 0.17.0 compiles the LaTeX paper; its TeX resource cache is separate from Python and was available on this machine. Initial TeX compilation on another machine may download TeX resources.

This revision uses the isolated Python 3.12.14 environment freshly installed for local revision R1 earlier on 22 September; the same locked environment is reused for R2 and R3 with the same locked package versions. results/run_manifest.json identifies the exact completed stages, timing, interpreter and input/code hashes of the delivered run. A full-analysis run re-estimates the supplied archived inputs, including 999 common parcel bootstrap refits and the new historical inventory exercise. A from-results run only rebuilds documents and must not be described as new estimation. The v3.1 full-analysis run took 39 minutes on eight cores (24 September 2026); a from-results run takes a few minutes. This is not independent multi-platform replication or a reconstruction of the original full raw panel.

## Run the package

Install Python 3.12 and Tectonic. Run the following commands from this replication directory. setup.sh creates a local virtual environment with the locked packages. Installation requires network access; analysis uses only supplied files. The TeX engine may need its resource cache during the first document build.

```sh
bash setup.sh
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 .venv/bin/python code/reproduce.py
```

The master is path-independent and can also be invoked by absolute path. It sets one OpenBLAS thread and stores its plotting configuration in tmp/matplotlib. It never refreshes APIs automatically. Its fixed random seeds are 20260909 for shared bootstrap draws and 20260910 for numerical audit selection and review queues. It stops on an analysis failure, rather than silently using existing results. Outputs are overwritten during intentional reruns; preserve a copy if comparing releases.

For a fast document rebuild from included results, append --from-results to the same master command. This skips statistical estimation and uses the delivered results; it does not independently verify them. The default command also runs market_conditions_extension.py and build_market_exhibits.py, then runs all baseline analyses, the outlier-robust estimators, instrument-pilot packaging, exhibits and documents.

The paper source and bibliography are in paper. code/build_exhibits.py regenerates all numerical tables, figures, model scenarios and TeX macros. code/build_support_documents.py builds this README.pdf and paper/disclosure.pdf from the supplied editable texts. In --from-results mode, delivered results regenerate the exhibits; source records are not re-estimated. The final release manifest fingerprints the delivered files; rerunning compressed outputs can change byte hashes through gzip metadata even when numerical content is identical.

## Program-to-exhibit map

- code/parse_rates.py: preserved annual page extracts to 574-row MORTGAGE30US.csv and coverage checks.
- code/analyze_repeat_sales.py: enriched house data; Tables 1 and 2; Figure 1; repeat_sales_results.json, cumulative_robustness.csv, joint_covariance.csv, paired_specification_differences.csv and the 999 common bootstrap draws. It also supplies the main classification and credit models.
- code/robust_estimators.py: Table 3, Huber and trimmed re-estimates of the headline and common borough-quarter house/condominium contrasts on the same 999 parcel-bootstrap draws; robust_estimates.json and robust_bootstrap_*.csv.
- code/related_party.py: Table 6, same-surname (probable related-party) deed flags and the company/other cash-buyer split, on the same 999 parcel-bootstrap draws; related_party.json, related_party_flags.csv, generated/related.tex and related_numbers.tex. `--from-results` rebuilds the table and macros from related_party.json.
- code/related_party_extensions.py: Table 7, the same-surname screen applied to houses and condominiums under the common borough-quarter design, and the shared-address sensitivity; related_party_extensions.json, generated/related_ext.tex and related_ext_numbers.tex. Inputs: data/condo_pairs_with_deeds.csv.gz, data/condo_parties.json.gz, data/house_party_addresses.json.gz (retrieval manifests data/condo_fetch_manifest.json and data/address_fetch_manifest.json; retrieval scripts in provenance/astra_v3_audit/).
- code/legal_rule_screen.py: lender take-title sensitivity (v3.2). Applies the companion paper's party-name classifier (When a Deed Is Not a Market Sale, module version 1.1.0, vendored unchanged as code/vendor/acris_consideration_filter.py, SHA-256 1b649ff08f9967b435a5f7da6696c432b03eee4d12799a11a7c762cc83c544f8; concept DOI 10.5281/zenodo.22925383) to the endpoint deeds of the 6,006 headline pairs and refits on the same 999 parcel-bootstrap draws; legal_rule_screen.json and generated/legal_numbers.tex. `--from-results` rebuilds the macros. The classifier's own document review is pending, so this is a sensitivity, not a correction.
- code/property_comparison.py: Table 4, common borough-quarter house/condominium estimates in property_comparison.json.
- code/analyze_repeat_sales.py plus additional_checks.py: Table 5, financing-window, institutional-name and unique-deed/amount sensitivities; Table 9, credit conditions and calendar-trend sensitivity.
- code/build_exhibits.py: Table 8, the conditional model inversion; model_inversion_scenarios.json. Failure probabilities are scenarios, not data estimates.
- code/analyze_coop_audit.py: Table 10 and the co-operative audit counts, with adjacency before classification filtering. Outputs include coop_assignment_audit.csv.gz and coop_estimate_sensitivity.json.
- code/market_conditions_extension.py and build_market_exhibits.py: Table 11, historical credit and inventory interactions with calendar dependence.
- code/focused_validation.py and build_focused_exhibits.py: Table 12, influence, geography and source-consistency refits, and the blinded review queue.
- code/additional_checks.py: numerical derivative checks, financing-window agreement and the distress adjudication queue.
- code/make_review_queues.py: the original 90+90 unreviewed sampling queues in results. The partially reviewed copies in audit are preserved separately.
- code/build_targeted_supplement.py: packages four explicitly recorded image readings and checks the mismatched unit has no repeat pair. It does not perform independent image adjudication.
- code/build_submission_documents.py: creates the anonymous manuscript source, cover letter, title page and submission copies.
- code/build_exhibits.py: renders the computational tables and the Figure 1 PNG from the named current outputs. publication_numbers.json is the current numerical summary used in document checks.

Tables are numbered by first appearance in paper.tex. Table source files under paper/generated have descriptive names to remain identifiable after editing. All code producing computational exhibits is supplied. CODEBOOK.md defines variables, classifications and raw-source documentation. TECHNICAL_METHODS.md gives the estimands, covariance derivation and sample construction.

## Quality checks and interpretation

The master enforces exact reproduction of the two original house residual point estimates, verifies rate coverage, checks timing-unique filing reuse and finite-difference derivatives, and saves all bootstrap draws. The release review checks manuscript references, numerical macros, output existence and the alignment of delivered copies. Statistical checks establish the implemented calculations, not exogeneity or ground-truth classification.

The house estimate is a conditional financing-associated contrast. Property comparisons have different selection and measurement. Rate interactions are trend-sensitive. All reported confidence intervals are pointwise and conditional on observed classifications. No journal acceptance probability or AEA certification is implied by the successful computational checks.

## Submission and version boundary

All manuscript tables, the appendix, pilot evidence, source inputs and code are included in this directory. The analysis starts from supplied archived inputs, not the missing original full raw extract. No full raw-to-paper verification or editor-approved exception is claimed. See CODEBOOK.md and TECHNICAL_METHODS.md for definitions and estimands.

The parent submission directory contains an anonymous review PDF, an identified complete PDF, separate title page, cover letter, disclosure and highlights. The anonymous PDF includes the entire appendix. Author identification remains in this replication package for provenance: use an editor/data-access file designation rather than treating it as anonymous reviewer material. Follow the submission portal's current file categories and instructions. No journal decision or deposit DOI is asserted.

The consolidated master resolves paths relative to this directory. Historical raw scripts under legacy_raw_pipeline are retained only as provenance and can contain old absolute paths. They are not called by the offline master. The manifest in the parent directory fingerprints the delivered package. A rerun may alter compressed/PDF byte hashes without changing estimates.


## September 22 corrections and exploratory extension

The headline house-gap specification and bootstrap are unchanged. The credit extension now includes uninteracted weekly PMMS rates at both endpoints: borough-quarter effects cannot absorb every within-quarter weekly movement. Revised credit tables supersede the earlier displayed slopes. The older rate-only outputs remain for transparent comparison and are explicitly identified as legacy specifications.

The one new market indicator is StreetEasy prior-month borough sales inventory, Single Family category, sourced from https://streeteasy.com/blog/data-dashboard/ and its Master Report download on 22 September 2026. data/streeteasy_totalInventory_Sfr.csv preserves the downloaded CSV. All 6,006 house pairs have both endpoints covered. This is a retrospective vintage with different property and listing coverage from the administrative sample. It is not a direct or exogenous liquidity measure. No present-day rent, vacancy or price statistics are added as historical regressors.

provenance/EXPLORATION_PLAN.md records the bounded plan made after coverage inspection but before fitting inventory associations. results/market_conditions_extension.json reports all four models, matching coverage, full covariance matrices, endpoint restrictions, residualized support and covariance corrections. The unaltered point estimates are accompanied by parcel-only and shared endpoint quarter/year inference. The latter uses inclusion-exclusion over shared calendar nodes and parcels, with an explicit direct-enumeration unit test. Finite-sample reference distributions and eigenvalue corrections are sensitivity diagnostics; ten calendar years do not provide reliable exact small-cluster inference.

Both the corrected credit and inventory interactions change materially with financing-specific calendar trends. They do not identify execution certainty, tax capitalization or a causal liquidity premium. See Appendix: Historical market conditions and shared calendar shocks.


## Focused validation pass (local R2)

code/focused_validation.py reconstructs the 6,006 house pairs from archived rows, checks endpoint consistency, computes exact coefficient weights, and refits all planned influence/geographic restrictions. It also reports source-triggered checks for ten pairs with ambiguous source dates and three financed endpoints without a positive mortgage amount. Combined record and source safeguards retain 5,579 pairs with a 9.02-log-point contrast. The main 9.25-log-point specification is unchanged.

The most adverse reported deletion removes 60 parcels selected for largest positive influence and reduces the contrast to 4.68 log points. Outcome-selected deletion is a diagnostic, not a new preferred sample; ordinary reported intervals do not account for selection. The outcome-perturbation scenarios hold financing labels and the design fixed and are not misclassification bounds. All fits are in results/focused_validation.json and focused_validation_refits.csv.

The new audit/focused_blinded_house_review.csv is prepared for an independent reader. Its analyst key includes selection information withheld from the reader-facing file. Forty randomly sampled switching pairs are distinct from targeted cases; their sample does not represent all house transactions. No new independent human reviews are claimed. audit/FOCUSED_REVIEW_PROTOCOL.md explains evidence and adjudication requirements. Both existing and new queues must remain unreviewed until actual documented examination occurs.

provenance/FOCUSED_VALIDATION_PLAN.md distinguishes the original pre-fit plan from source-triggered additions. code/build_focused_exhibits.py builds the new appendix table from saved results. The default master includes these stages; --from-results regenerates the exhibit without rerunning estimation. This release does not refresh raw government sources or reconstruct the original raw panel.


## R3: outlier-robust estimates and removal of the transfer-tax appendix

code/robust_estimators.py adds robust Huber (k=1.345, two-stage MAD scale) and trimmed (1/99 and 2.5/97.5 percentiles of annualized growth) estimates of the joint contrast using conventional tuning constants. They reuse the 999 common parcel-bootstrap draws; the code asserts that its least-squares row reproduces the published 9.25-log-point interval before reporting robust intervals. They answer the adverse influence-selected deletion reported in R2 with estimators that do not select on the fitted contrast.

The 2019 transfer-tax threshold analysis, charm-price financing comparison and tax-design discussion were removed from the manuscript and the build. They overlapped with the companion paper The Shape of the Tax, which reports that analysis from the same archived price sample. The three scripts that produced it (analyze_notches.py, notch_sample_checks.py, check_reform_design.py) are no longer part of this package; they remain in the parent Zenodo version 2.0 and in the companion paper's own replication deposit.

## V2.2: interpretation and documentation corrections (23 September 2026)

Release WGTH-2026-09-23-V2.2 implements five narrowly scoped interpretation and documentation corrections following an independent audit:
1. Conditioned the execution-risk calculation: clarified that the 87% loss at 10% failure risk illustrates model demands under stated assumptions rather than identifying an empirical bound on the mechanism.
2. Accurately stated robust estimands: removed claims that OLS overstates the contrast for a "typical pair"; stated that the house contrast remains positive but sensitive to extreme appreciation.
3. Described condominiums precisely: noted that the condominium contrast is much smaller and sensitive to the estimator (0.77 OLS with interval including zero; -0.49 Huber).
4. Replaced "pre-specified" with "robust estimators using conventional tuning constants".
5. Removed the speculative France comparative sentence from the conclusion.
All numerical results, estimates, bootstrap intervals and sample counts are unchanged.

## V3.0: related-party transfers and the identity of the cash buyer (24 September 2026)

Version 3.0 adds one analysis, code/related_party.py (Table 6, new Section 5), and rewrites the title, abstract, introduction and conclusion around its result. No earlier estimate changes; the headline 9.25 [7.17, 11.35] and all robust estimates are reproduced exactly and the script asserts that its least-squares bootstrap interval equals the published one.

- Flag: a deed at either endpoint on which a natural-person grantor and grantee share a surname (ACRIS party extract data/parties.json; company, trust and estate names never match). A strict variant ignores the 40 most frequent surnames in the extract.
- 358 of 6,006 headline pairs are flagged (238 under the strict flag). Same-surname deeds are 5.7% of unfinanced endpoints and 2.3% of financed endpoints.
- Excluding flagged pairs: least squares 4.87 [2.69, 6.76], paired change −4.38 [−5.63, −3.18]; Huber 4.02 [2.28, 5.73]; trims 4.03 and 2.83. Strict flag: 6.71 [4.69, 8.72].
- Cash buyer is a company (explicit corporate form): 1.53 [−1.79, 5.44]; other cash buyers 13.77 [10.96, 15.98]; after excluding flagged pairs 1.55 and 7.11 [4.48, 9.12].
- Seller-model requirement at q = 0.1 for the contrast without flagged pairs: 45% of price (37% at Huber).
- Tables formerly numbered 6–10 are now 7–11.
- Runtime: related_party.py took 19 minutes in the clean full run of 24 September 2026 (999 draws, each with least squares, Huber and two trims on three samples plus two splits); the whole master script took 29 minutes.

The party extract covers house deeds only, so condominium estimates are not adjusted. A shared surname is a proxy for a relationship: it misses relatives with different surnames and can match unrelated people.

## V3.2: lender take-title sensitivity (25 September 2026)

`code/legal_rule_screen.py` applies the companion deed classifier (vendored, module 1.1.0) to the 6,006 headline pairs and refits on the common 999 draws: 93 flagged pairs; excluding them gives 9.78 [7.73, 11.84], a paired change of +0.52 [0.19, 0.97]; with the same-surname screen, 5.35 [3.23, 7.35]. Output: results/legal_rule_screen.json and paper/generated/legal_numbers.tex. This stage was run on 25 September 2026 with Python 3.14.7 and current NumPy, pandas and SciPy rather than the pinned 3.12 environment; the script asserts that it reproduces the published headline (9.25) and the published bootstrap interval of the headline to 1e-7 before reporting anything, and both checks passed. It took 82 minutes on eight cores. No other stage was rerun for v3.2; the manuscript was rebuilt with Tectonic. The analyst key (`audit/focused_review_ANALYST_KEY.csv`) is not in the public v3.2 archive, so that reviewers cannot see the answers. Its SHA-256 is `c57075d1462c944cd784f1b7ad44b2c2c71c9708bc7011e73ad9de84723c0ca0`. `code/focused_validation.py` regenerates the same file deterministically from the archived inputs and seeds, so anyone can confirm the key after the review. Earlier archives (v3.1) did include it; reviewers are asked not to open any package or repository for this paper until both sheets are locked.

## V3.1: condominium screen, shared-address sensitivity and wording (24 September 2026)

- New code/related_party_extensions.py (Table 7). It recomputes, with this package's design and bootstrap draws, the independent audit preserved in provenance/astra_v3_audit/ and matches it exactly.
  - Common borough-quarter design, same-surname pairs excluded: houses 11.42 → 7.50 [6.00, 9.19] (449 flagged of 8,208); condominiums 0.77 → −0.46 [−1.16, 0.14] (189 flagged of 6,584), paired change −1.23 [−1.71, −0.82]; strict condominium flag −0.26 [−0.97, 0.34].
  - Condominium deeds linked for 13,092 of 13,168 endpoints; 31 ambiguous matches left unlinked. Every linked condominium deed has party records.
  - Headline house specification, also excluding shared grantor/grantee mailing addresses: 3.76 [1.16, 6.05]; additional change −1.11 [−2.76, 0.29]. Natural-person addresses only: 4.41 [2.14, 6.75]. Shared addresses are about equally common at cash and financed endpoints and are not evidence of kinship.
- related_party.py now counts an endpoint as covered when its linked deed has any party record. v3.0 counted only deeds with a natural-person name and understated coverage (89%/88%); the correct figures are 97.8% and 98.7%, equal to deed-linkage coverage. No estimate changes.
- Wording: the reduction from 9.25 to 4.87 is described as the change after excluding flagged pairs, not as a share of the gap caused by family transfers.
- Tables formerly numbered 7–11 are now 8–12.
- Deed-image review: code/deed_review_summary.py summarizes audit/deed_image_review/deed_review_readings.csv (60 deeds, AI-assisted readings of the RP-5217NYC transfer reports, confirmed by the author). Flagged 16/40 show a non-market sign (40%, Wilson CI 26–55%); unflagged cash 2/20 (10%, 3–30%). Outputs: results/deed_review_summary.json, paper/generated/deed_numbers.tex. The 684 page images are not redistributed; audit/deed_image_review/download.py re-downloads them from ACRIS.
