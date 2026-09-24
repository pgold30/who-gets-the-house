# Revision notes: Who Gets the House?

Pablo Loschi · ORCID 0009-0004-9455-4713 · concept DOI 10.5281/zenodo.22421850

All numbers are in log points (100 × log-price difference) unless stated otherwise. Intervals are 95% percentile intervals from the same 999 parcel-bootstrap draws (seed 20260909) in v2.1–v3.1.

---

## v3.1 (24 September 2026): condominium screen, shared-address sensitivity, precise wording

An independent audit reproduced every v3.0 flag and estimate exactly (preserved in `replication/provenance/astra_v3_audit/`). v3.1 adds its two extensions, recomputed with the package's own code (`code/related_party_extensions.py`, new Table 7).

**Condominiums, screened the same way.**
- *Linkage:* condominium deeds are linked for 13,092 of 13,168 endpoints, with 31 ambiguous matches left unlinked. The surname rule flags 189 of 6,584 condominium pairs.
- *Common borough-quarter design:*
  - houses fall from 11.42 to **7.50 [6.00, 9.19]**;
  - condominiums move from 0.77 to **−0.46 [−1.16, 0.14]**, a paired change of −1.23 [−1.71, −0.82];
  - the strict flag gives −0.26 [−0.97, 0.34].
- The divergence between houses and condominiums survives the screen.

**Shared mailing address.**
- *Effect:* also excluding pairs whose deed shows the seller and buyer at the same normalized street address, city and ZIP lowers the headline house contrast to 3.76 [1.16, 6.05]. The additional change, −1.11 [−2.76, 0.29], is not distinguishable from zero. Counting natural persons only gives 4.41 [2.14, 6.75].
- *Caveat:* shared addresses are about equally common at cash and financed sales (16.7% vs 17.2%) and include common mailing agents. They are not evidence of kinship.

**Wording.**
- The fall from 9.25 to 4.87 is now described as the change after excluding flagged pairs, not as a share of the gap caused by family transfers.
- Same-surname deeds are described as a marker of *possible* transfers between relatives.

**Coverage figure corrected.** Linked deeds with party records cover 97.8% of first-sale and 98.7% of resale endpoints. v3.0 counted only deeds naming a natural person and reported 89% and 88%. No estimate is affected.

**Deed-image review (new Appendix and `code/deed_review_summary.py`).**
- *Sample and method:* a random sample of 40 flagged and 20 unflagged cash deeds (seed 20260924), drawn by the independent audit, was read from the ACRIS images. Each reading uses the state transfer report (RP-5217NYC) filed with the deed, cross-checked against the transfer taxes paid. The readings were AI-assisted and confirmed by the author.
- *Result:* 16 of 40 flagged deeds (40%, 95% CI 26–55%) declare a sale between relatives, a buyer who is also a seller or a non-standard deed, or report a $0 price with no transfer tax. Among unflagged cash deeds the share is 2 of 20 (10%, 3–30%). Another 9 flagged deeds show a shared address or an owner on both sides.
- *Caveat:* declarations are self-reported, so these shares are lower bounds.
- *Files:* readings, image crops and scripts are in `replication/audit/deed_image_review/`.

**Citation.** The companion paper is now cited as the *Shape of the Tax* preprint (doi:10.5281/zenodo.22925302), with its v1.3 replication package (doi:10.5281/zenodo.22924780).

**Numbering.** Tables formerly numbered 7–11 are now 8–12.

---

## v3.0 (24 September 2026): related-party transfers and the identity of the cash buyer

**New title:** *Who Gets the House? Related-Party Transfers and the Cash–Mortgage Price Gap in New York City*. It was previously *Financing-Associated Price Gaps in New York City*.

### New analysis

A new Section 5 and Table 6 (`code/related_party.py`) ask who the cash buyer is.

**1. Same-surname transfers.**
- *What the flag is:* a deed at either endpoint on which a natural-person seller and buyer share a surname. These are probable transfers within families, which need not be priced at arm's length. Company, trust and estate names never match.
- *Why it matters:* such transfers sit on the cash side of *both* switching arms. They raise appreciation in cash-to-financed pairs and lower it in financed-to-cash pairs, so they inflate the contrast. The symmetry diagnostic cannot see them, because the two movements cancel in its sum.
- *How common they are:*
  - 358 of the 6,006 headline pairs are flagged.
  - Same-surname deeds are 5.7% of unfinanced sales and 2.3% of financed sales.
  - Flagged cash-to-financed pairs appreciate 0.65 in log price, against 0.34 for the rest. Flagged financed-to-cash pairs *fall* 0.27, while the rest rise 0.20.
- *Effect of excluding them:* the house contrast falls from **9.25 [7.17, 11.35] to 4.87 [2.69, 6.76]**. The paired change is −4.38 [−5.63, −3.18].
  - Huber: 4.02 [2.28, 5.73].
  - Trims: 4.03 and 2.83.
- *Strict flag,* which ignores the 40 most common surnames: 6.71 [4.69, 8.72].

**2. Company versus other cash buyers.**
- *Company is the cash buyer:* the contrast is **1.53 [−1.79, 5.44]**.
- *Anyone else is the cash buyer:* 13.77 [10.96, 15.98]; 7.11 [4.48, 9.12] after excluding same-surname pairs.
- *Relation to earlier versions:* the replication packages of versions 1 and 2.0 included a simpler split of pairs into individual-to-individual and business pairs, which later versions dropped. v3.0 splits by the buyer at the cash sale, inside the headline joint model, with paired bootstrap inference. The same-surname screen is new.

**3. Seller-model calibration, updated.** At an assumed 10% failure probability, the contrast without same-surname pairs requires a loss of 45% of the price on a failed sale (37% at Huber). The headline requires 87%, and condominiums about 7%.

### Rewritten text

- **Title, abstract, introduction and conclusion** are rewritten around the result: the measured cash discount mostly reflects *who* buys with cash, not what closing certainty is worth.
- **The literature discussion** is folded into the introduction.
- **The conclusion** adds a policy paragraph on taxes and subsidies tied to the payment method. It cites the 1% tax on NYC cash home purchases of $1 million or more that New York legislators considered in May 2026 and then dropped from the state budget (Bloomberg, 14 and 21 May 2026). The paper does not evaluate that proposal.
- **The sample period** is now stated explicitly: sales from 2016–2025, with first sales in 2016–2022 and resales in 2019–2025.

### Unchanged

- Every earlier estimate, sample and bootstrap draw. `related_party.py` asserts that its least-squares interval equals the published one.

### Package

- **Top level** is simplified to this file, `START_HERE.md`, the manuscript PDF, `replication/` and `submission/`.
- **Version-specific changelogs and validation reports** from v2.2 and v2.3 are folded into these notes.
- **Tables** formerly numbered 6–10 are now 7–11.

### Limits added

- A shared surname is a proxy for a relationship. It misses relatives with different surnames and can match unrelated people.
- Party records cover 89% and 88% of first-sale and resale endpoints. *(Corrected in v3.1: the true figures are 97.8% and 98.7%.)*
- The party extract covers house deeds only, so condominium estimates are not adjusted. *(Done in v3.1.)*

---

## v2.3 (23 September 2026; doi:10.5281/zenodo.22921991)

Documentation-only fix. The v2.2 documentation gave the condominium least-squares interval as [−0.12, 1.66], a value no output supports. The correct figure is **[−0.01, 1.56]**, as the manuscript had always reported. The manuscript and code were byte-identical to v2.2.

## v2.2 (23 September 2026; doi:10.5281/zenodo.22921254)

Interpretation corrections after an independent audit; no estimate changed.
- The 87% execution-risk figure is now described as an illustrative calibration, not an empirical bound.
- The house contrast is described as positive but sensitive to extreme appreciation.
- The condominium contrast is described as much smaller and sensitive to the estimator.
- "Pre-specified" is replaced by "robust estimators using conventional tuning constants".
- A speculative sentence about France is removed.

## v2.1 (22 September 2026; doi:10.5281/zenodo.22915008)

- **Outlier-robust estimates added:** Huber (k = 1.345, two-stage MAD scale) and trimming of annualized growth at 1/99 and 2.5/97.5. They run on the common bootstrap draws and give 5.15–7.66 for houses.
- **Transfer-tax threshold appendix removed.** It duplicated the companion paper *The Shape of the Tax* (doi:10.5281/zenodo.22880953).

## v2.0 (15 September 2026; doi:10.5281/zenodo.22770065)

Retitled *Financing-Associated Price Gaps in New York City*. This version still contained the transfer-tax threshold analysis that v2.1 moved to the companion paper.

## v1 (6 September 2026; doi:10.5281/zenodo.22421851)

First deposit, titled *Who Gets the House? Execution Certainty, the Mortgage Recording Tax, and the Design of Transfer Taxes in New York City*.
