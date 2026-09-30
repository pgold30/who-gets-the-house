# Revision notes: Who Gets the House?

Pablo Loschi · ORCID 0009-0004-9455-4713 · concept DOI 10.5281/zenodo.22421850

All numbers are in log points (100 × log-price difference) unless stated otherwise. Intervals are 95% percentile intervals from the same 999 parcel-bootstrap draws (seed 20260909) used since v2.1.

## v3.5 (30 September 2026): label errors in both directions and related to growth

- **What v3.4 left open.** Its stress test recoded cash labels at random, in one direction, inside the switching arms. It did not model financed labels that are really cash, cash–cash or financed–financed pairs that would become switchers, or errors related to price growth. New Table 14 (Appendix G; `code/misclassification_checks.py`) covers all three on the same corrected sample, with the 49 reviewed pairs fixed.
- **Random errors in both directions**, at the review's rates and upper limits (8% or 18.8% of cash labels hiding a mortgage; 0, 3.6% or 6.4% of financed labels really cash), pull the contrast toward zero, to 5.82–8.96 log points on average, without changing its sign. The surname screen still removes 47–51%.
- **The documented failure modes** barely move it: late or early recording gives 8.75, and hidden mortgages only among company buyers give 9.26–9.39.
- **Errors related to growth** can reverse it. With labels drawn more often where recoding works against the contrast, it reaches zero when the recoded labels' mean standardized effect is 0.70 (0.45 without same-surname pairs); choosing the most influential labels bounds it between −15.70 and 25.49. The review is too small to rule such a pattern out, and the abstract, conclusion and appendix now say so.
- **Joint table (new Table 15).** The documented corrections and the screens together, on the common bootstrap: 5.19 [2.98, 7.18] on 5,520 pairs, a change of −4.06 [−5.36, −2.76] from the published estimate.
- **Unchanged.** Every earlier estimate. These checks were specified in an AI assessment (ChatGPT) of v3.4 and run by Claude.

## v3.4 (29 September 2026): conditional stress test; review wording

- **Stress test (new Table 13, Appendix G; `code/financing_stress_test.py`).** How far would the contrast move if unreviewed cash labels hid purchase mortgages like those the review found?
  - Design: start from the corrected sample (9.40; 4.89 without same-surname pairs) and keep the 49 remaining reviewed pairs fixed. Then recode at random 10%, 15% or 36% of the unreviewed financed-to-cash pairs, and 0%, 8% or 16% of the unreviewed cash-to-financed pairs, from cash to financed; 200 draws per cell. The same recoded data are fitted with and without same-surname pairs.
  - Results: the mean contrast stays between 9.13 and 9.34 (4.69–4.87 without same-surname pairs). The surname screen removes 48–49% of the contrast in every cell.
  - Limits: the shares are scenarios informed by the detected discrepancies, and the ranges are percentiles of point estimates, not confidence intervals. The test does not model errors correlated with price growth, financed labels that are really cash, or cash–cash pairs that would become switchers.
- **Correction.** v3.3 said that misclassifying financed purchases as cash would, if anything, shrink the contrast. The documented corrections raise it slightly, but the random recoding lowers it slightly, so the direction depends on which pairs carry the errors. The sentence now says so.
- **Review wording.** v3.3 described the review as "two independent AI readings". ChatGPT read the documents and Claude then checked each reading against ACRIS open data; Claude did not read the images. The abstract, Appendix G, conclusion, declarations, cover letter and review files now say this. The rates measure agreement with the readings, not accuracy against a verified record.
- **Unchanged.** No other estimate. An earlier version of the stress test, run outside the package, was reproduced exactly by an AI cross-check (ChatGPT/Codex), whose three requested changes are made here.

## v3.3 (28 September 2026): instrument review of the 53-pair queue

- **Review.** The original protocol called for two human readers; this version uses AI (v3.4 wording: ChatGPT read the documents and Claude then checked each reading against open data). ChatGPT read the deed and candidate mortgages for all 106 endpoints; Claude checked each reading against ACRIS open data and returned five for a second look. Readings were locked before the analyst key was opened; the key (SHA-256 c57075d1…0ca0, as published with v3.2) is now deposited.
- **Results.** 54 of 56 financed labels are confirmed by a documented purchase mortgage. 4 of 50 cash labels (8%; 95% interval 3–19%) have a same-day purchase mortgage: two because the city's index dates the mortgage or the deed a year from its true date, two because the loan is recorded against two adjoining lots. No reading establishes a cash purchase, so pair-level error bounds stay wide (6.2–100% in the probability arms).
- **Headline.** Dropping the four pairs with a documented error gives 9.40 log points (analytic interval [7.59, 11.21]) against 9.25 [7.44, 11.07] on the same interval. The bootstrap headline and every other estimate are unchanged.
- **Text.** Abstract, conclusion, Appendix (focused validation) and the generative-AI statement updated. New macros in `paper/generated/review_numbers.tex`, written by `code/cross_ai_review.py`, which the master now runs.

## v3.2 (25 September 2026): lender take-title sensitivity, companion links, review queue

The companion paper *When a Deed Is Not a Market Sale* shows that foreclosure and deed-in-lieu transfers to lenders can record an amount set by a legal rule instead of a price. v3.2 applies that paper's party-name classifier (module version 1.1.0, copied unchanged to `replication/code/vendor/acris_consideration_filter.py`) to the deeds linked to the 6,006 headline pairs, using `replication/code/legal_rule_screen.py` and the same 999 bootstrap draws.

The classifier flags 93 pairs. Of their 96 flagged endpoints, 93 are unfinanced, so these lenders enter the analysis as cash buyers, and 38 of the pairs survive the broader institution exclusion. The classifier's broad option flags 145 pairs. Excluding the 93 pairs raises the house contrast from 9.25 to 9.78 [7.73, 11.84], a paired change of +0.52 [0.19, 0.97]. The broad option gives 9.76 [7.69, 11.75], and combining the screen with the same-surname exclusion gives 5.35 [3.23, 7.35] against 4.87, a change of +0.48 [0.13, 0.96]. The direction is what legal-rule amounts imply. The classifier's own error rates await its document review, so this is a sensitivity analysis, not a correction, and the conclusions do not change.

Other changes:

- The introduction cites both companion papers by concept DOI. The policy paragraph now matches its sources: the May 2026 cash-purchase tax was reported as likely to be dropped from the state budget.
- The appendix on the same-surname deed reading says the sample was drawn by a seeded script, and that the readings, which were AI-assisted and confirmed by the author, are not an independent human review.
- The 53-pair focused queue (40 probability-sampled pairs and 13 targeted diagnostics) is named as the blinded two-reader review. The older 90+90 queues are kept but are not the evidence gate.
- The declaration names the generative-AI tools used: OpenAI's ChatGPT and Codex, Anthropic's Claude and Google's Gemini.
- The anonymous-submission builder also anonymizes the new companion citation, and the submission copies were rebuilt.
- The public archive no longer includes the analyst key for the blinded review (`replication/audit/focused_review_ANALYST_KEY.csv`), which v3.1 did include. Its SHA-256 is `c57075d1462c944cd784f1b7ad44b2c2c71c9708bc7011e73ad9de84723c0ca0`, and `code/focused_validation.py` regenerates it deterministically, so it can be checked after the review.
- No other estimate changed.

## v3.1 (24 September 2026): condominium screen, shared-address sensitivity, precise wording

An independent audit reproduced every v3.0 flag and estimate exactly; its files are in `replication/provenance/astra_v3_audit/`. v3.1 adds the audit's two extensions, recomputed with the package's own code (`code/related_party_extensions.py`, new Table 7).

Condominiums are screened the same way as houses. Condominium deeds are linked for 13,092 of 13,168 endpoints, with 31 ambiguous matches left unlinked, and the surname rule flags 189 of 6,584 condominium pairs. Under the common borough-quarter design, houses fall from 11.42 to 7.50 [6.00, 9.19]. Condominiums move from 0.77 to −0.46 [−1.16, 0.14], a paired change of −1.23 [−1.71, −0.82], and the strict flag gives −0.26 [−0.97, 0.34]. The gap between houses and condominiums survives the screen.

A shared-mailing-address screen additionally excludes pairs whose deed shows the seller and buyer at the same normalized street address, city and ZIP. It lowers the headline house contrast to 3.76 [1.16, 6.05]. The additional change, −1.11 [−2.76, 0.29], is not distinguishable from zero, and counting natural persons only gives 4.41 [2.14, 6.75]. Shared addresses are about as common at cash sales as at financed ones (16.7% against 17.2%) and include common mailing agents, so they are not evidence of kinship.

The wording changed in two places. The fall from 9.25 to 4.87 is described as the change after excluding flagged pairs, not as the share of the gap caused by family transfers, and same-surname deeds are described as a marker of possible transfers between relatives.

The coverage figure was corrected: linked deeds with party records cover 97.8% of first-sale and 98.7% of resale endpoints. v3.0 counted only deeds naming a natural person and reported 89% and 88%. No estimate is affected.

A new appendix and `code/deed_review_summary.py` report a deed-image review. The independent audit drew a random sample of 40 flagged and 20 unflagged cash deeds (seed 20260924), and each was read from its ACRIS image using the state transfer report (RP-5217NYC) filed with the deed, cross-checked against the transfer taxes paid. The readings were AI-assisted and confirmed by the author. Of the 40 flagged deeds, 16 (40%, 95% CI 26–55%) declare a sale between relatives, a buyer who is also a seller or a non-standard deed, or report a $0 price with no transfer tax. Among unflagged cash deeds the share is 2 of 20 (10%, 3–30%), and another 9 flagged deeds show a shared address or an owner on both sides. The declarations are self-reported, so these shares are lower bounds. Readings, image crops and scripts are in `replication/audit/deed_image_review/`.

The companion paper is cited as the *Shape of the Tax* preprint (doi:10.5281/zenodo.22925302), with its v1.3 replication package (doi:10.5281/zenodo.22924780). Tables formerly numbered 7–11 are now 8–12.

## v3.0 (24 September 2026): related-party transfers and the identity of the cash buyer

The paper was retitled *Who Gets the House? Related-Party Transfers and the Cash–Mortgage Price Gap in New York City*; the previous subtitle was *Financing-Associated Price Gaps in New York City*.

A new Section 5 and Table 6 (`code/related_party.py`) ask who the cash buyer is.

The first analysis flags same-surname transfers: deeds at either endpoint on which a natural-person seller and buyer share a surname. These are probable transfers within families, which need not be priced at arm's length; company, trust and estate names never match. Such transfers sit on the cash side of both switching arms. They raise appreciation in cash-to-financed pairs and lower it in financed-to-cash pairs, which inflates the contrast, and the symmetry diagnostic cannot see them because the two movements cancel in its sum. The flag marks 358 of the 6,006 headline pairs. Same-surname deeds are 5.7% of unfinanced sales and 2.3% of financed sales. Flagged cash-to-financed pairs appreciate 0.65 in log price, against 0.34 for the rest, and flagged financed-to-cash pairs fall 0.27 while the rest rise 0.20. Excluding flagged pairs moves the house contrast from 9.25 [7.17, 11.35] to 4.87 [2.69, 6.76], a paired change of −4.38 [−5.63, −3.18]; Huber gives 4.02 [2.28, 5.73] and the trims give 4.03 and 2.83. A strict flag that ignores the 40 most common surnames gives 6.71 [4.69, 8.72].

The second analysis splits pairs by the buyer at the cash sale. When a company pays cash, the contrast is 1.53 [−1.79, 5.44]. When anyone else does, it is 13.77 [10.96, 15.98], or 7.11 [4.48, 9.12] after excluding same-surname pairs. The replication packages of versions 1 and 2.0 had a simpler split into individual-to-individual and business pairs, which later versions dropped; v3.0 splits by the buyer at the cash sale inside the headline joint model, with paired bootstrap inference. The same-surname screen is new.

The seller-model calibration was updated. At an assumed 10% failure probability, the contrast without same-surname pairs requires a loss of 45% of the price on a failed sale (37% at Huber), against 87% for the headline contrast and about 7% for condominiums.

The title, abstract, introduction and conclusion were rewritten around the main result: the measured cash discount mostly reflects who buys with cash, not what closing certainty is worth. The literature discussion moved into the introduction. The conclusion added a policy paragraph on taxes and subsidies tied to the payment method, citing the 1% tax on New York City cash home purchases of $1 million or more that legislators considered in May 2026 (Bloomberg, 14 and 21 May 2026); v3.0 described it as dropped from the budget, and v3.2 corrects this to "reported as likely to be dropped", which is what the sources say. The paper does not evaluate the proposal. The sample period is stated explicitly: sales from 2016–2025, with first sales in 2016–2022 and resales in 2019–2025.

Every earlier estimate, sample and bootstrap draw is unchanged, and `related_party.py` checks that its least-squares interval equals the published one.

The package was simplified. The top level holds this file, `START_HERE.md`, the manuscript PDF, `replication/` and `submission/`; the version-specific changelogs and validation reports from v2.2 and v2.3 were folded into these notes; and tables formerly numbered 6–10 became 7–11.

v3.0 also added limitations. A shared surname is a proxy for a relationship: it misses relatives with different surnames and can match unrelated people. Party-record coverage was reported as 89% and 88% of first-sale and resale endpoints (corrected in v3.1 to 97.8% and 98.7%). The party extract then covered house deeds only, so condominium estimates were not adjusted (done in v3.1).

## v2.3 (23 September 2026; doi:10.5281/zenodo.22921991)

A documentation-only fix. The v2.2 documentation gave the condominium least-squares interval as [−0.12, 1.66], a value no output supports. The correct figure, [−0.01, 1.56], is the one the manuscript had always reported. The manuscript and code were byte-identical to v2.2.

## v2.2 (23 September 2026; doi:10.5281/zenodo.22921254)

Interpretation corrections after an independent audit, with no estimate changed. The 87% execution-risk figure is described as an illustrative calibration, not an empirical bound. The house contrast is described as positive but sensitive to extreme appreciation, and the condominium contrast as much smaller and sensitive to the estimator. "Pre-specified" was replaced by "robust estimators using conventional tuning constants", and a speculative sentence about France was removed.

## v2.1 (22 September 2026; doi:10.5281/zenodo.22915008)

Outlier-robust estimates were added: Huber (k = 1.345, two-stage MAD scale) and trimming of annualized growth at 1/99 and 2.5/97.5. They run on the common bootstrap draws and give 5.15–7.66 for houses. The transfer-tax threshold appendix was removed because it duplicated the companion paper *The Shape of the Tax* (doi:10.5281/zenodo.22880953).

## v2.0 (15 September 2026; doi:10.5281/zenodo.22770065)

Retitled *Financing-Associated Price Gaps in New York City*. This version still contained the transfer-tax threshold analysis that v2.1 moved to the companion paper.

## v1 (6 September 2026; doi:10.5281/zenodo.22421851)

First deposit, titled *Who Gets the House? Execution Certainty, the Mortgage Recording Tax, and the Design of Transfer Taxes in New York City*.
