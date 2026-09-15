# Replication README

Who Gets the House? Financing-Associated Price Gaps in New York City

Pablo Loschi, independent researcher, Berlin. Contact: loschi.pablo@gmail.com. Submission version WGTH-2026-09-10-JHE-S1, prepared 10 September 2026. This self-contained package accompanies paper/paper.pdf for Journal of Housing Economics. It requires no earlier revision folders. Nothing has been submitted or uploaded by this workflow.

## Computational scope and unresolved omissions

The inherited clean analysis run reproduces the baseline calculations from the four supplied archived inputs and preserved public-data extracts. It rebuilds enriched house pairs, co-operative assignments, estimates, covariance, 999 bootstrap refits, numerical checks, nine baseline tables, two figures and the conditional model grid. It does not reconstruct the original house/condominium panel from the full raw DOF/ACRIS extract. That exact raw vintage is absent from the supplied local files and linked GitHub snapshot. No non-public-data exemption or editor-approved waiver is claimed.

The original raw-stage scripts are preserved under legacy_raw_pipeline for provenance, but contain historical paths and an incomplete retrieval-to-analysis integration. Their retrieval wrapper writes NDJSON while linkage scripts expect other filenames/formats, and it is not the master script for this revision. Refreshing today's APIs is a new data vintage, not proof of exact reconstruction of the original extract. Recovering the original raw inputs and running an integrated raw build remains necessary before claiming full raw-to-paper replication.

The consolidated audit includes AI-assisted image review of two house and two co-operative cases, with independent human review pending. One co-operative filing pledges a different unit from its assigned sale; that sale enters no repeat pair and its rejection does not change the estimates. The 90+90 queues remain incomplete. Saved evidence and case notes are in audit; no population accuracy rate or classification-adjusted estimate is claimed. These remain substantive measurement limitations.

## Provenance of the four archived inputs

All four files under inputs are byte-identical to the author's repository https://github.com/pgold30/who-gets-the-house at commit f404e48320a81e3bfe20127af2ed7c2d9fb5268e, retrieved 10 September 2026. Their individual SHA-256 comparisons are in provenance/github_input_comparison.json. This immutable commit identifies the consulted source; it is not a substitute for a trusted repository deposit with a permanent identifier.

- inputs/2_reproduce/panel2.csv.gz: archived merged house/condominium panel; 290,840 sales, including 249,395 outside Staten Island. SHA-256 a99671affb4d16190e064a998f62541bffa3976bcd432cfd365ff26ddcc8a6c5.
- inputs/2_reproduce/dob_permits.csv.gz: original permit snapshot. SHA-256 1785534a084b78ae117d94c5997944b65b0d03a00aa51734570b7a26b4cb2baf.
- inputs/3_section4.9/deeds_for_pairs.json: original date/document lookup for house parcels. SHA-256 5a3914253109fd3cf3c097de7660121363e051168257b6a688521777f7f4b349.
- inputs/4_full_pipeline/sample_2016_2025.csv.gz: archived 431,471-sale citywide price sample. SHA-256 495d66ab48b781fc6b0d02015b15ecf6049a1843e255e0a23f6786ef264bced9.

The earlier repository README includes a Zenodo badge. That identifier has not been adopted as the identifier for this revision. The author confirms that no paper publication is to be updated; current instructions prepare a first public working-paper release and make no claim about an existing deposit.

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

The inherited baseline master run took 101.6 seconds on this host, including 78.8 seconds for house preparation and bootstrap refits. Allow roughly two to six minutes depending on initialization and host performance. Its original log is provenance/inherited_analysis_run_manifest.json. The submission assembly was checked using the existing results, without rerunning the unchanged bootstrap or creating another environment. results/run_manifest.json records the mode and stages of the most recent consolidated build; it must not be described as a fresh clean full-analysis run when mode is from-results. Figure font-cache initialization may add time on first use. Hardware model and total memory were unavailable through the sandbox, and are not invented. This is one clean installation and host, not an independent multi-platform replication.

## Run the package

Install Python 3.12 and Tectonic. Run the following commands from this replication directory. setup.sh creates a local virtual environment with the locked packages. Installation requires network access; analysis uses only supplied files. The TeX engine may need its resource cache during the first document build.

```sh
bash setup.sh
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 .venv/bin/python code/reproduce.py
```

The master is path-independent and can also be invoked by absolute path. It sets one OpenBLAS thread and stores its plotting configuration in tmp/matplotlib. It never refreshes APIs automatically. Its fixed random seeds are 20260909 for shared bootstrap draws and 20260910 for numerical audit selection and review queues. It stops on an analysis failure, rather than silently using existing results. Outputs are overwritten during intentional reruns; preserve a copy if comparing releases.

For a fast document rebuild from included results, append --from-results to the same master command. This skips statistical estimation and uses the delivered results; it does not independently verify them. The default command runs all baseline analyses, the targeted reform checks, instrument-pilot packaging, exhibits and documents.

The paper source and bibliography are in paper. code/build_exhibits.py regenerates all numerical tables, figures, model scenarios and TeX macros. code/build_support_documents.py builds this README.pdf and paper/disclosure.pdf from the supplied editable texts. In --from-results mode, delivered results regenerate the exhibits; source records are not re-estimated. The new targeted-period table is generated by code/build_targeted_supplement.py. The final release manifest fingerprints the delivered files; rerunning compressed outputs can change byte hashes through gzip metadata even when numerical content is identical.

## Program-to-exhibit map

- code/parse_rates.py: preserved annual page extracts to 574-row MORTGAGE30US.csv and coverage checks.
- code/analyze_repeat_sales.py: enriched house data; Tables 1 and 2; Figure 1; repeat_sales_results.json, cumulative_robustness.csv, joint_covariance.csv, paired_specification_differences.csv and the 999 common bootstrap draws. It also supplies the main classification and credit models.
- code/property_comparison.py: Table 3, common borough-quarter house/condominium estimates in property_comparison.json.
- code/analyze_repeat_sales.py plus additional_checks.py: Table 4, financing-window, institutional-name and unique-deed/amount sensitivities; Table 5, credit conditions and calendar-trend sensitivity.
- code/analyze_coop_audit.py: Table 7 and the co-operative audit counts, with adjacency before classification filtering. Outputs include coop_assignment_audit.csv.gz and coop_estimate_sensitivity.json.
- code/build_exhibits.py: Table 6, the conditional model inversion; model_inversion_scenarios.json. Failure probabilities are scenarios, not data estimates.
- code/analyze_notches.py: Table 8 and Figure 2, common pre/post count-ratio and annual placebo-adjusted outputs. Sample sensitivities come from notch_sample_checks.py.
- code/additional_checks.py: Table 9, adjusted charm-price financing composition; also numerical derivative checks and financing-window agreement.
- code/make_review_queues.py: the original 90+90 unreviewed sampling queues in results. The partially reviewed copies in audit are preserved separately.
- code/check_reform_design.py: 45 period/bandwidth comparisons, nine pre-period tests and six geographical diagnostics; source inputs remain the archived price sample.
- code/build_targeted_supplement.py: packages four explicitly recorded image readings, checks the mismatched unit has no repeat pair, and generates Table 10. It does not perform independent image adjudication.
- code/build_submission_documents.py: creates the anonymous manuscript source, cover letter, title page and submission copies.
- code/build_exhibits.py: renders the nine tables and two PNG figures from the named current outputs. publication_numbers.json is the current numerical summary used in document checks.

Tables are numbered by first appearance in paper.tex. Table source files under paper/generated have descriptive names to remain identifiable after editing. All code producing computational exhibits is supplied. CODEBOOK.md defines variables, classifications and raw-source documentation. TECHNICAL_METHODS.md gives the estimands, covariance derivation and sample construction.

## Quality checks and interpretation

The master enforces exact reproduction of the two original house residual point estimates, verifies rate coverage, checks timing-unique filing reuse and finite-difference derivatives, and saves all bootstrap draws. The release review checks manuscript references, numerical macros, output existence and the alignment of delivered copies. Statistical checks establish the implemented calculations, not exogeneity or ground-truth classification.

The house estimate is a conditional financing-associated contrast. Property comparisons have different selection and measurement. Rate interactions are trend-sensitive. Price-count ratios are not transaction-destruction rates or welfare estimates. All reported confidence intervals are pointwise and conditional on observed classifications. No journal acceptance probability or AEA certification is implied by the successful computational checks.

## Submission and version boundary

All manuscript tables, the appendix, pilot evidence, source inputs and code are included in this directory. The analysis starts from supplied archived inputs, not the missing original full raw extract. No full raw-to-paper verification or editor-approved exception is claimed. See CODEBOOK.md and TECHNICAL_METHODS.md for definitions and estimands.

The parent submission directory contains an anonymous review PDF, an identified complete PDF, separate title page, cover letter, disclosure and highlights. The anonymous PDF includes the entire appendix. Author identification remains in this replication package for provenance: use an editor/data-access file designation rather than treating it as anonymous reviewer material. Follow the submission portal's current file categories and instructions. No journal decision or deposit DOI is asserted.

The consolidated master resolves paths relative to this directory. Historical raw scripts under legacy_raw_pipeline are retained only as provenance and can contain old absolute paths. They are not called by the offline master. The manifest in the parent directory fingerprints the delivered package. A rerun may alter compressed/PDF byte hashes without changing estimates.
